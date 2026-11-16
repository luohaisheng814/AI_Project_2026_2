package com.busan.tour;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Base64;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Locale;
import java.util.UUID;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import javax.crypto.SecretKeyFactory;
import javax.crypto.spec.PBEKeySpec;

/**
 * 釜山 AI 旅行助手 v2.3
 *
 * v2.3 修复实时定位链路：GPS 按钮统一走原生 LocationManager；权限已授予时启动自动恢复
 * 实时定位；15 秒无坐标给出可操作提示；权限被拒绝时不再重复弹窗。
 * 地图按钮明确标注 NAVER / Google 归属；景点回答上方内置 1-3 张实景图。
 *
 * v2.2 修复路线问句被行程规划抢答：地名错字（甘村/看川）先归一；
 * 显式路线问句优先走实时定位路线卡，并按直线距离给“最优建议”；
 * 官方资料块只给网址，不再展示官网韩文原文；
 * v2.1 把“玩法/出行”合并成可折叠条：默认展开，7 秒无操作自动收起；
 * 官方资料块只给网址，不再展示官网韩文原文；
 * 按一人男/一人女/两人男女/两人男男/两人女女/三人以上给出差异化点位与路线。
 *
 * v2.0 补入海云台、广安里、太宗台、札嘎其等 10 个釜山核心景点；
 * 路线不再写死甘川，任意收录景点都能从当前位置出 3 类走法；
 * 新增“当前位置去其他景点”的最近 3 点路线、附近问答和通用智能建议。
 *
 * v1.9.1 修正“有几条路线/怎么去/从当前位置去”被 planner 当成行程规划的问题，
 * 这类明确路线问题优先进入定位权限与实时路线流程。
 *
 * v1.8.1 增加云端意图解析：纠正错字、识别“上午去哪”和“从当前位置去某地”，
 * 把“库里没有这个地点”改成真正可执行的推荐/路线回答。
 *
 * v1.8 取消端侧模型与 379 MB 模型下载，改为「联网即用」的免费云端模型：
 *   - 内置 Kilo Gateway 匿名免费接入，默认 NVIDIA Nemotron 3.5 Super VL（开放权重）；
 *   - 不需要 API Key，联网后问答/行程自动调用；离线自动回退包内规则与快照；
 *   - 仍保留自定义 OpenAI 兼容接口的能力，方便换模型或自建网关。
 *
 * v1.5 起已有的本地账户、会话、偏好持久化、实时定位与网络回调保持不变。
 */
public class MainActivity extends Activity {

    private static final String AUTH_PREFS = "busan_auth";
    private static final String LLM_PREFS = "busan_llm";
    private static final long SESSION_TTL_MS = 30L * 24L * 60L * 60L * 1000L;
    private static final int PBKDF2_ROUNDS = 100000;

    /** 默认云端：Kilo Gateway 匿名免费层，无需 API Key；模型为开放权重的 Nemotron 3.5 Super VL。 */
    private static final String DEFAULT_LLM_ENDPOINT = "https://ai-gateway.kilo.ai/api/v1";
    private static final String DEFAULT_LLM_MODEL = "nvidia/nemotron-3.5-super-vl:free";
    private static final String DEFAULT_LLM_PROVIDER = "Kilo Gateway · Free";

    private WebView web;
    private final ExecutorService pool = Executors.newFixedThreadPool(3);
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private SharedPreferences authPrefs;
    private SharedPreferences llmPrefs;

    private ConnectivityManager.NetworkCallback networkCallback;
    private Runnable netNotifyRunnable;
    private boolean pageReady = false;

    private LocationManager locationManager;
    private LocationListener locationListener;
    private boolean watchWanted = false;
    private boolean watchRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        authPrefs = getSharedPreferences(AUTH_PREFS, Context.MODE_PRIVATE);
        llmPrefs = getSharedPreferences(LLM_PREFS, Context.MODE_PRIVATE);

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setGeolocationEnabled(true);
        s.setSupportZoom(false);
        s.setTextZoom(100);
        s.setAllowFileAccess(true);
        s.setAllowContentAccess(true);
        if (Build.VERSION.SDK_INT >= 21) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        web.addJavascriptInterface(new HostBridge(), "BusanHost");

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                                                           GeolocationPermissions.Callback callback) {
                callback.invoke(origin, true, false);
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                pageReady = true;
                notifyNetworkSoon();
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(url);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest req) {
                return handleUrl(req.getUrl().toString());
            }
        });

        registerNetworkCallback();
        web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (watchWanted) startLocationInternal();
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopLocationInternal();
    }

    @Override
    protected void onDestroy() {
        stopLocationInternal();
        unregisterNetworkCallback();
        super.onDestroy();
    }

    /** file:// 留在应用内；地图深链、官网链接交给系统或外部浏览器。 */
    private boolean handleUrl(String url) {
        if (url == null) return false;
        if (url.startsWith("file://")) return false;

        if (url.startsWith("http://") || url.startsWith("https://")) {
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
            } catch (Exception e) {
                toast("没有可用的浏览器");
            }
            return true;
        }

        if (url.startsWith("intent:")) {
            try {
                Intent i = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
                startActivity(i);
            } catch (Exception e) {
                toast("未找到可打开该链接的地图 App，请用网页地图");
            }
            return true;
        }

        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception e) {
            toast("未找到可打开该链接的地图 App，请用网页地图");
        }
        return true;
    }

    private void toast(String msg) {
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show();
    }

    private void js(String code) {
        if (web == null) return;
        try {
            web.evaluateJavascript(code, null);
        } catch (Exception ignored) {
        }
    }

    private void jsStringCall(String fn, String value) {
        js("window." + fn + "&&window." + fn + "(" + JSONObject.quote(value == null ? "" : value) + ");");
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    /* ================= 网络 ================= */

    private boolean isNetAllowed() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            if (Build.VERSION.SDK_INT >= 23) {
                Network n = cm.getActiveNetwork();
                if (n == null) return false;
                NetworkCapabilities c = cm.getNetworkCapabilities(n);
                return c != null
                        && c.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                        && c.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED);
            }
            android.net.NetworkInfo info = cm.getActiveNetworkInfo();
            return info != null && info.isConnected();
        } catch (Exception e) {
            return false;
        }
    }

    private void registerNetworkCallback() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return;
            NetworkRequest request = new NetworkRequest.Builder()
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                    .build();
            networkCallback = new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    notifyNetworkSoon();
                }

                @Override
                public void onLost(Network network) {
                    notifyNetworkSoon();
                }

                @Override
                public void onCapabilitiesChanged(Network network, NetworkCapabilities caps) {
                    notifyNetworkSoon();
                }
            };
            cm.registerNetworkCallback(request, networkCallback);
        } catch (Exception ignored) {
        }
    }

    private void unregisterNetworkCallback() {
        if (networkCallback == null) return;
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) cm.unregisterNetworkCallback(networkCallback);
        } catch (Exception ignored) {
        }
        networkCallback = null;
    }

    private void notifyNetworkSoon() {
        if (netNotifyRunnable != null) mainHandler.removeCallbacks(netNotifyRunnable);
        netNotifyRunnable = new Runnable() {
            @Override
            public void run() {
                if (!pageReady) return;
                js("window.__busanNetChanged&&window.__busanNetChanged(" + isNetAllowed() + ");");
            }
        };
        mainHandler.postDelayed(netNotifyRunnable, 250);
    }

    /* ================= 账户与会话 ================= */

    private String sha256Hex(String value) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] bytes = md.digest(value.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte b : bytes) sb.append(String.format(Locale.US, "%02x", b));
            return sb.toString();
        } catch (Exception e) {
            return "";
        }
    }

    private String randomBase64(int bytes) {
        byte[] buf = new byte[bytes];
        new SecureRandom().nextBytes(buf);
        return Base64.encodeToString(buf, Base64.NO_WRAP);
    }

    private String deriveHash(String password, String saltB64) throws Exception {
        PBEKeySpec spec = new PBEKeySpec(password.toCharArray(),
                Base64.decode(saltB64, Base64.NO_WRAP), PBKDF2_ROUNDS, 256);
        SecretKeyFactory factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA1");
        byte[] out = factory.generateSecret(spec).getEncoded();
        return Base64.encodeToString(out, Base64.NO_WRAP);
    }

    private String keyOfUsername(String username) {
        return sha256Hex(username.trim().toLowerCase(Locale.US));
    }

    private JSONObject users() {
        try {
            return new JSONObject(authPrefs.getString("users", "{}"));
        } catch (Exception e) {
            return new JSONObject();
        }
    }

    private void saveUsers(JSONObject users) {
        authPrefs.edit().putString("users", users.toString()).apply();
    }

    private void clearSession() {
        String key = authPrefs.getString("session_user", "");
        if (!key.isEmpty()) {
            JSONObject users = users();
            JSONObject rec = users.optJSONObject(key);
            if (rec != null) {
                rec.remove("sessionToken");
                try {
                    users.put(key, rec);
                    saveUsers(users);
                } catch (Exception ignored) {
                }
            }
        }
        authPrefs.edit()
                .remove("session_user")
                .remove("session_token")
                .remove("session_last")
                .apply();
    }

    private JSONObject readSession(int[] state) {
        String key = authPrefs.getString("session_user", "");
        String token = authPrefs.getString("session_token", "");
        if (key.isEmpty() || token.isEmpty()) {
            state[0] = 0;
            return null;
        }
        JSONObject users = users();
        JSONObject rec = users.optJSONObject(key);
        if (rec == null || !token.equals(rec.optString("sessionToken", ""))) {
            clearSession();
            state[0] = 0;
            return null;
        }
        long last = rec.optLong("lastActive", 0L);
        if (System.currentTimeMillis() - last > SESSION_TTL_MS) {
            clearSession();
            state[0] = 2;
            return null;
        }
        state[0] = 1;
        return rec;
    }

    private JSONObject touchRecord(JSONObject rec) {
        try {
            rec.put("lastActive", System.currentTimeMillis());
        } catch (Exception ignored) {
        }
        return rec;
    }

    private JSONObject userPayload(JSONObject rec) throws Exception {
        JSONObject user = new JSONObject();
        user.put("username", rec.optString("username"));
        user.put("displayName", rec.optString("displayName", rec.optString("username")));
        user.put("createdAt", rec.optLong("createdAt", 0L));
        user.put("lastLogin", rec.optLong("lastLogin", 0L));
        user.put("lastActive", rec.optLong("lastActive", 0L));
        JSONObject out = new JSONObject();
        out.put("ok", true);
        out.put("user", user);
        return out;
    }

    private String error(String code, String message) {
        try {
            JSONObject out = new JSONObject();
            out.put("ok", false);
            out.put("error", code);
            out.put("message", message);
            return out.toString();
        } catch (Exception e) {
            return "{\"ok\":false,\"error\":\"unknown\"}";
        }
    }

    @JavascriptInterface
    public String authRegister(String username, String password, String displayName) {
        username = username == null ? "" : username.trim();
        password = password == null ? "" : password;
        displayName = displayName == null ? "" : displayName.trim();
        if (username.length() < 2 || username.length() > 24) {
            return error("username_length", "用户名需为 2–24 个字符");
        }
        if (password.length() < 6) {
            return error("password_length", "密码至少 6 位");
        }
        if (displayName.isEmpty()) displayName = username;
        if (displayName.length() > 24) displayName = displayName.substring(0, 24);

        String key = keyOfUsername(username);
        JSONObject users = users();
        if (users.has(key)) return error("user_exists", "这个用户名已经注册");

        try {
            String salt = randomBase64(16);
            JSONObject rec = new JSONObject();
            rec.put("username", username);
            rec.put("displayName", displayName);
            rec.put("salt", salt);
            rec.put("hash", deriveHash(password, salt));
            rec.put("createdAt", System.currentTimeMillis());
            rec.put("lastLogin", System.currentTimeMillis());
            rec.put("lastActive", System.currentTimeMillis());
            String token = UUID.randomUUID().toString();
            rec.put("sessionToken", token);
            users.put(key, rec);
            saveUsers(users);
            authPrefs.edit()
                    .putString("session_user", key)
                    .putString("session_token", token)
                    .putLong("session_last", System.currentTimeMillis())
                    .apply();
            return userPayload(rec).toString();
        } catch (Exception e) {
            return error("hash_failed", "注册失败，请重试");
        }
    }

    @JavascriptInterface
    public String authLogin(String username, String password) {
        username = username == null ? "" : username.trim();
        password = password == null ? "" : password;
        if (username.isEmpty() || password.isEmpty()) {
            return error("empty", "请输入用户名和密码");
        }
        String key = keyOfUsername(username);
        JSONObject users = users();
        JSONObject rec = users.optJSONObject(key);
        if (rec == null) return error("invalid_credentials", "用户名或密码不正确");
        try {
            String hash = deriveHash(password, rec.optString("salt"));
            if (!MessageDigest.isEqual(hash.getBytes("UTF-8"),
                    rec.optString("hash").getBytes("UTF-8"))) {
                return error("invalid_credentials", "用户名或密码不正确");
            }
            String token = UUID.randomUUID().toString();
            rec.put("sessionToken", token);
            rec.put("lastLogin", System.currentTimeMillis());
            rec.put("lastActive", System.currentTimeMillis());
            users.put(key, rec);
            saveUsers(users);
            authPrefs.edit()
                    .putString("session_user", key)
                    .putString("session_token", token)
                    .putLong("session_last", System.currentTimeMillis())
                    .apply();
            return userPayload(rec).toString();
        } catch (Exception e) {
            return error("login_failed", "登录失败，请重试");
        }
    }

    @JavascriptInterface
    public String authCurrent() {
        int[] state = {0};
        JSONObject rec = readSession(state);
        if (rec == null) {
            if (state[0] == 2) {
                return error("expired", "登录已超过 30 天未使用，已自动退出");
            }
            return error("none", "未登录");
        }
        try {
            touchRecord(rec);
            JSONObject users = users();
            users.put(authPrefs.getString("session_user", ""), rec);
            saveUsers(users);
            authPrefs.edit().putLong("session_last", System.currentTimeMillis()).apply();
            return userPayload(rec).toString();
        } catch (Exception e) {
            return error("session_failed", "读取登录状态失败");
        }
    }

    @JavascriptInterface
    public String authLogout() {
        clearSession();
        return "{\"ok\":true}";
    }

    @JavascriptInterface
    public String saveUserState(String json) {
        int[] state = {0};
        JSONObject rec = readSession(state);
        if (rec == null) return "{\"ok\":false,\"error\":\"auth\"}";
        if (json == null || json.length() > 200000) {
            return "{\"ok\":false,\"error\":\"too_large\"}";
        }
        try {
            new JSONObject(json);
        } catch (Exception e) {
            return "{\"ok\":false,\"error\":\"bad_json\"}";
        }
        String key = authPrefs.getString("session_user", "");
        authPrefs.edit().putString("state_" + key, json).apply();
        touchRecord(rec);
        JSONObject users = users();
        try {
            users.put(key, rec);
            saveUsers(users);
        } catch (Exception ignored) {
        }
        return "{\"ok\":true}";
    }

    @JavascriptInterface
    public String loadUserState() {
        int[] state = {0};
        JSONObject rec = readSession(state);
        if (rec == null) return "{}";
        return authPrefs.getString("state_" + authPrefs.getString("session_user", ""), "{}");
    }

    /* ================= 大模型（OpenAI 兼容） ================= */

    private String llmEndpoint() {
        String e = llmPrefs.getString("endpoint", "").trim();
        return e.isEmpty() ? DEFAULT_LLM_ENDPOINT : e;
    }

    private String llmKey() {
        return llmPrefs.getString("api_key", "").trim();
    }

    private String llmModel() {
        String m = llmPrefs.getString("model", "").trim();
        return m.isEmpty() ? DEFAULT_LLM_MODEL : m;
    }

    private boolean llmBuiltin() {
        return llmPrefs.getString("endpoint", "").trim().isEmpty()
                && llmPrefs.getString("model", "").trim().isEmpty();
    }

    private boolean llmReady() {
        return !llmEndpoint().isEmpty() && !llmModel().isEmpty();
    }

    private String llmConfigJson() {
        try {
            JSONObject out = new JSONObject();
            out.put("endpoint", llmEndpoint());
            out.put("model", llmModel());
            out.put("provider", llmBuiltin() ? DEFAULT_LLM_PROVIDER : "custom");
            out.put("builtin", llmBuiltin());
            out.put("hasKey", !llmKey().isEmpty());
            String key = llmKey();
            out.put("keyTail", key.length() > 4 ? key.substring(key.length() - 4) : "");
            return out.toString();
        } catch (Exception e) {
            return "{}";
        }
    }

    @JavascriptInterface
    public boolean llmConfigured() {
        return llmReady();
    }

    @JavascriptInterface
    public String getLlmConfig() {
        return llmConfigJson();
    }

    @JavascriptInterface
    public String saveLlmConfig(String endpoint, String apiKey, String model) {
        endpoint = endpoint == null ? "" : endpoint.trim();
        apiKey = apiKey == null ? "" : apiKey.trim();
        model = model == null ? "" : model.trim();
        if (!endpoint.isEmpty() && !endpoint.startsWith("http://") && !endpoint.startsWith("https://")) {
            return error("endpoint_scheme", "接口地址需以 http:// 或 https:// 开头");
        }
        SharedPreferences.Editor ed = llmPrefs.edit();
        if (!endpoint.isEmpty()) ed.putString("endpoint", endpoint);
        if (!apiKey.isEmpty()) ed.putString("api_key", apiKey);
        if (!model.isEmpty()) ed.putString("model", model);
        ed.apply();
        return "{\"ok\":true,\"config\":" + llmConfigJson() + "}";
    }

    @JavascriptInterface
    public String clearLlmConfig() {
        llmPrefs.edit().clear().apply();
        return "{\"ok\":true}";
    }

    private String normalizeEndpoint(String endpoint) {
        String e = endpoint.trim();
        while (e.endsWith("/")) e = e.substring(0, e.length() - 1);
        if (e.endsWith("/chat/completions")) return e;
        return e + "/chat/completions";
    }

    private void llmCallback(final String cbId, final int status, final String body) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                js("window.__busanLlmDone&&window.__busanLlmDone(" +
                        JSONObject.quote(cbId) + "," + status + "," +
                        JSONObject.quote(body == null ? "" : body) + ");");
            }
        });
    }

    @JavascriptInterface
    public void llmChat(final String messagesJson, final String cbId) {
        if (!llmReady()) {
            llmCallback(cbId, -2, "{\"error\":\"llm_not_configured\"}");
            return;
        }
        pool.execute(new Runnable() {
            @Override
            public void run() {
                int status = -1;
                String body = "";
                HttpURLConnection conn = null;
                try {
                    JSONArray messages = new JSONArray(messagesJson);
                    JSONObject payload = new JSONObject();
                    payload.put("model", llmModel());
                    payload.put("messages", messages);
                    payload.put("temperature", 0.2);
                    payload.put("max_tokens", 900);
                    payload.put("stream", false);
                    if (DEFAULT_LLM_MODEL.equals(llmModel())) {
                        // 默认模型自带推理段；关闭后直接输出答案/JSON，避免 900 token 被推理耗尽。
                        payload.put("reasoning_effort", "none");
                    }

                    URL u = new URL(normalizeEndpoint(llmEndpoint()));
                    conn = (HttpURLConnection) u.openConnection();
                    conn.setConnectTimeout(15000);
                    conn.setReadTimeout(60000);
                    conn.setRequestMethod("POST");
                    conn.setDoOutput(true);
                    conn.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                    if (!llmKey().isEmpty()) {
                        conn.setRequestProperty("Authorization", "Bearer " + llmKey());
                    }
                    conn.setRequestProperty("Accept", "application/json");
                    conn.setRequestProperty("User-Agent", "BusanTour/2.3 (Android)");
                    byte[] bytes = payload.toString().getBytes("UTF-8");
                    OutputStream os = conn.getOutputStream();
                    os.write(bytes);
                    os.flush();
                    os.close();

                    status = conn.getResponseCode();
                    InputStream in = (status >= 200 && status < 400)
                            ? conn.getInputStream() : conn.getErrorStream();
                    if (in != null) {
                        BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
                        StringBuilder sb = new StringBuilder();
                        String line;
                        while ((line = br.readLine()) != null) sb.append(line).append('\n');
                        br.close();
                        body = sb.toString();
                    }
                } catch (Exception e) {
                    status = -1;
                    body = "{\"error\":\"network\"}";
                } finally {
                    if (conn != null) conn.disconnect();
                }
                llmCallback(cbId, status, body);
            }
        });
    }

    /* ================= 定位 ================= */

    private boolean hasLocationPermission() {
        if (Build.VERSION.SDK_INT < 23) return true;
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED;
    }

    public void openAppSettings() {
        try {
            Intent i = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                    Uri.parse("package:" + getPackageName()));
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Exception e) {
            toast("请到系统设置里为本应用开启定位权限");
        }
    }

    @JavascriptInterface
    public boolean startLocationWatch() {
        watchWanted = true;
        if (!hasLocationPermission()) {
            if (Build.VERSION.SDK_INT >= 23) {
                requestPermissions(new String[]{
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION}, 1002);
            }
            return false;
        }
        startLocationInternal();
        return true;
    }

    @JavascriptInterface
    public void stopLocationWatch() {
        watchWanted = false;
        stopLocationInternal();
    }

    private void startLocationInternal() {
        if (watchRunning || !hasLocationPermission()) return;
        try {
            locationManager = (LocationManager) getSystemService(Context.LOCATION_SERVICE);
            if (locationManager == null) return;
            locationListener = new LocationListener() {
                @Override
                public void onLocationChanged(Location location) {
                    emitLocation(location);
                }

                @Override
                public void onStatusChanged(String provider, int status, Bundle extras) {
                }

                @Override
                public void onProviderEnabled(String provider) {
                }

                @Override
                public void onProviderDisabled(String provider) {
                }
            };

            String[] providers = new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER};
            for (String p : providers) {
                try {
                    if (locationManager.isProviderEnabled(p)) {
                        locationManager.requestLocationUpdates(p, 3000L, 12.0f, locationListener,
                                Looper.getMainLooper());
                    }
                } catch (Exception ignored) {
                }
            }
            Location last = bestLastKnown();
            if (last != null) emitLocation(last);
            watchRunning = true;
        } catch (Exception e) {
            js("window.__busanLocError&&window.__busanLocError(2,'location_unavailable');");
        }
    }

    private Location bestLastKnown() {
        Location best = null;
        try {
            String[] providers = new String[]{LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER};
            for (String p : providers) {
                Location l = locationManager.getLastKnownLocation(p);
                if (l == null) continue;
                if (best == null || l.getTime() > best.getTime()) best = l;
            }
        } catch (Exception ignored) {
        }
        return best;
    }

    private void stopLocationInternal() {
        if (!watchRunning || locationManager == null || locationListener == null) {
            watchRunning = false;
            return;
        }
        try {
            locationManager.removeUpdates(locationListener);
        } catch (Exception ignored) {
        }
        watchRunning = false;
    }

    private void emitLocation(Location l) {
        if (l == null) return;
        final String code = "window.__busanLocUpdate&&window.__busanLocUpdate("
                + String.format(Locale.US, "%.6f", l.getLatitude()) + ","
                + String.format(Locale.US, "%.6f", l.getLongitude()) + ","
                + Math.round(l.getAccuracy()) + ","
                + JSONObject.quote(l.getProvider() == null ? "" : l.getProvider()) + ","
                + l.getTime() + ");";
        js(code);
    }

    /* ================= JS 桥 ================= */

    class HostBridge {

        @JavascriptInterface
        public boolean llmConfigured() {
            return MainActivity.this.llmConfigured();
        }

        @JavascriptInterface
        public String getLlmConfig() {
            return MainActivity.this.getLlmConfig();
        }

        @JavascriptInterface
        public String saveLlmConfig(String endpoint, String apiKey, String model) {
            return MainActivity.this.saveLlmConfig(endpoint, apiKey, model);
        }

        @JavascriptInterface
        public String clearLlmConfig() {
            return MainActivity.this.clearLlmConfig();
        }

        @JavascriptInterface
        public void llmChat(String messagesJson, String cbId) {
            MainActivity.this.llmChat(messagesJson, cbId);
        }

        @JavascriptInterface
        public boolean netAllowed() {
            return isNetAllowed();
        }

        /** 异步 GET：结果回到 window.__busanHttpDone(id, status, body)。 */
        @JavascriptInterface
        public void fetchText(final String url, final String cbId) {
            pool.execute(new Runnable() {
                @Override
                public void run() {
                    int status = -1;
                    String body = "";
                    HttpURLConnection conn = null;
                    try {
                        URL u = new URL(url);
                        conn = (HttpURLConnection) u.openConnection();
                        conn.setConnectTimeout(12000);
                        conn.setReadTimeout(15000);
                        conn.setInstanceFollowRedirects(true);
                        conn.setRequestProperty("User-Agent",
                                "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110 Mobile Safari/537.36");
                        conn.setRequestProperty("Accept-Language", "ko-KR,ko;q=0.9,en;q=0.6");
                        conn.setRequestProperty("Accept", "text/html,application/json,*/*");
                        if (url.contains("saha.go.kr")) {
                            conn.setRequestProperty("Referer", "https://www.saha.go.kr/tour/");
                        }
                        status = conn.getResponseCode();
                        InputStream in = (status >= 200 && status < 400) ? conn.getInputStream() : conn.getErrorStream();
                        if (in != null) {
                            BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
                            StringBuilder sb = new StringBuilder();
                            String line;
                            while ((line = br.readLine()) != null) sb.append(line).append('\n');
                            br.close();
                            body = sb.toString();
                        }
                    } catch (Exception e) {
                        status = -1;
                    } finally {
                        if (conn != null) conn.disconnect();
                    }
                    final int st = status;
                    final String payload = body;
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            js("window.__busanHttpDone&&window.__busanHttpDone(" + JSONObject.quote(cbId) + ","
                                    + st + "," + JSONObject.quote(payload) + ");");
                        }
                    });
                }
            });
        }

        @JavascriptInterface
        public void requestLocation() {
            if (Build.VERSION.SDK_INT >= 23 && !hasLocationPermission()) {
                requestPermissions(new String[]{
                        Manifest.permission.ACCESS_FINE_LOCATION,
                        Manifest.permission.ACCESS_COARSE_LOCATION}, 1001);
                return;
            }
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    js("window.__busanLocReady&&window.__busanLocReady();");
                }
            });
        }

        @JavascriptInterface
        public boolean hasLocationPermission() {
            return MainActivity.this.hasLocationPermission();
        }

        @JavascriptInterface
        public boolean startLocationWatch() {
            return MainActivity.this.startLocationWatch();
        }

        @JavascriptInterface
        public void stopLocationWatch() {
            MainActivity.this.stopLocationWatch();
        }

        @JavascriptInterface
        public void openAppSettings() {
            MainActivity.this.openAppSettings();
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        boolean granted = false;
        for (int r : grantResults) if (r == PackageManager.PERMISSION_GRANTED) granted = true;
        if (requestCode == 1001) {
            if (granted) {
                web.postDelayed(new Runnable() {
                    @Override
                    public void run() {
                        js("window.__busanLocReady&&window.__busanLocReady();");
                    }
                }, 300);
            } else {
                js("window.__busanLocError&&window.__busanLocError(1,'permission_denied');");
            }
        } else if (requestCode == 1002) {
            if (granted) {
                startLocationInternal();
            } else {
                watchWanted = false;
                js("window.__busanLocError&&window.__busanLocError(1,'permission_denied');");
            }
        }
    }
}
