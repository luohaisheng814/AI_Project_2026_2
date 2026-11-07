package com.busan.tour;

import android.Manifest;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * 釜山 AI 旅行助手 v1.3（云端直连版）
 *
 * 与 v1.2 的区别：不再要求用户填写「电脑地址」，也不再区分「连电脑 / 离线」。
 * 联网与离线的分界线只有一条——手机本身允不允许这个 App 访问它当前所连的网络：
 *   · 允许且有网：页面自己从云端数据库（GitHub raw）取景点档案，并直接抓景点官网正文；
 *   · 不允许 / 没网：页面自动退回包内快照，全功能离线可用。
 * 本 Activity 只做三件事：开 WebView、给网页一个受控的 HTTP 通道、把定位与地图深链交给系统。
 */
public class MainActivity extends Activity {

    private WebView web;
    private final ExecutorService pool = Executors.newFixedThreadPool(3);

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setGeolocationEnabled(true);
        s.setSupportZoom(false);
        s.setTextZoom(100);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        if (Build.VERSION.SDK_INT >= 21) {
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        web.addJavascriptInterface(new HostBridge(), "BusanHost");

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                                                           GeolocationPermissions.Callback callback) {
                // 系统级定位授权由 requestLocation() 在运行时申请；这里放行网页侧的 origin
                callback.invoke(origin, true, false);
            }
        });

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(url);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, android.webkit.WebResourceRequest req) {
                return handleUrl(req.getUrl().toString());
            }
        });

        web.loadUrl("file:///android_asset/index.html");
    }

    /** file:// 留在应用内；地图深链、官网链接交给系统或外部浏览器。 */
    private boolean handleUrl(String url) {
        if (url == null) return false;
        if (url.startsWith("file://")) return false;

        if (url.startsWith("http://") || url.startsWith("https://")) {
            // 页面内的「官网 / 网页地图」链接：用系统浏览器打开，别把应用顶掉
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

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    /** 网页与系统之间的唯一通道。 */
    class HostBridge {

        /** 手机当前是否允许本 App 使用它连接的网络（飞行模式 / 无网络 / 系统限制都会返回 false）。 */
        @JavascriptInterface
        public boolean netAllowed() {
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
                            try {
                                web.evaluateJavascript("window.__busanHttpDone(" + JSONObject.quote(cbId) + ","
                                        + st + "," + JSONObject.quote(payload) + ");", null);
                            } catch (Exception ignored) {
                            }
                        }
                    });
                }
            });
        }

        @JavascriptInterface
        public void requestLocation() {
            if (Build.VERSION.SDK_INT >= 23) {
                if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
                        && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{
                            Manifest.permission.ACCESS_FINE_LOCATION,
                            Manifest.permission.ACCESS_COARSE_LOCATION}, 1001);
                    return;
                }
            }
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    try {
                        web.evaluateJavascript("window.__busanLocReady&&window.__busanLocReady();", null);
                    } catch (Exception ignored) {
                    }
                }
            });
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == 1001) {
            web.postDelayed(new Runnable() {
                @Override
                public void run() {
                    try {
                        web.evaluateJavascript("window.__busanLocReady&&window.__busanLocReady();", null);
                    } catch (Exception ignored) {
                    }
                }
            }, 300);
        }
    }
}
