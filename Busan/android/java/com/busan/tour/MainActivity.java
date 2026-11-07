package com.busan.tour;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

/**
 * 安装包外壳（1.2）：
 *  · 联网模式：加载电脑/服务器上的手机版服务（登录、景点官网检索、NAVER 深链全部走服务端）；
 *  · 离线模式：没有配置服务器时，加载安装包内置的 data.js 离线问答页；
 *  · 定位：Android 6+ 运行时授权 + WebView 地理定位回调，授权结果通过 __busanLocReady 回给网页；
 *  · 地图：nmap:// / navermaps:// / intent:// 等 scheme 交给系统，直接唤起 NAVER 地图等 App。
 */
public class MainActivity extends Activity {

    private static final int REQ_LOCATION = 1001;
    private static final String PREFS = "busan_prefs";
    private static final String K_SERVER = "server_url";
    private static final String K_OFFLINE = "offline_mode";

    private WebView web;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        prefs = getSharedPreferences(PREFS, MODE_PRIVATE);

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setGeolocationEnabled(true);          // WebView 侧允许地理定位
        s.setTextZoom(100);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                return handleUrl(view, url);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                if (Build.VERSION.SDK_INT >= 21) {
                    return handleUrl(view, request.getUrl().toString());
                }
                return false;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (Build.VERSION.SDK_INT >= 21 && request.isForMainFrame()) {
                    // 服务器连不上：回到设置页，让用户改地址或改用离线模式
                    if (view.getUrl() != null && view.getUrl().startsWith("http")) {
                        view.loadUrl("file:///android_asset/setup.html");
                    }
                }
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                                                           GeolocationPermissions.Callback callback) {
                // 页面已经通过 BusanHost.requestLocation() 拿到系统权限，这里只放行 WebView 的地理定位
                callback.invoke(origin, true, false);
            }
        });

        web.addJavascriptInterface(new HostBridge(), "BusanHost");
        openStartPage();
    }

    /** 有已保存的服务器就用联网版，否则进设置页（设置页里可以选离线模式）。 */
    private void openStartPage() {
        String server = prefs.getString(K_SERVER, "");
        boolean offline = prefs.getBoolean(K_OFFLINE, false);
        if (!offline && server != null && server.length() > 0) {
            web.loadUrl(server);
        } else if (offline) {
            web.loadUrl("file:///android_asset/index.html");
        } else {
            web.loadUrl("file:///android_asset/setup.html");
        }
    }

    private String normalize(String raw) {
        String u = raw == null ? "" : raw.trim();
        if (u.length() == 0) return "";
        if (!u.startsWith("http://") && !u.startsWith("https://")) {
            u = "http://" + u;
        }
        if (!u.endsWith("/")) u = u + "/";
        return u;
    }

    /** http(s) 在 WebView 内打开；nmap:// 等外部 scheme 交给系统 App。 */
    private boolean handleUrl(WebView view, String url) {
        if (url == null) return false;
        String lower = url.toLowerCase();
        if (lower.startsWith("http://") || lower.startsWith("https://")) {
            return false;                      // 默认行为：WebView 内加载
        }
        if (lower.startsWith("file://")) {
            return false;
        }
        try {
            Intent intent;
            if (lower.startsWith("intent:")) {
                intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
            } else {
                intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
            }
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(intent);
        } catch (Exception e) {
            // 没装对应地图 App：前端还有「网页地图 / Google」兜底，这里只提示一次
            Toast.makeText(this, "未找到可打开该链接的地图 App，请用网页地图", Toast.LENGTH_SHORT).show();
        }
        return true;
    }

    /** 网页侧桥：服务器地址、离线开关、定位授权。 */
    private class HostBridge {

        @JavascriptInterface
        public void setServer(String url) {
            final String norm = normalize(url);
            if (norm.length() == 0) return;
            prefs.edit().putString(K_SERVER, norm).putBoolean(K_OFFLINE, false).apply();
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    web.loadUrl(norm);
                }
            });
        }

        @JavascriptInterface
        public String getServer() {
            return prefs.getString(K_SERVER, "");
        }

        @JavascriptInterface
        public void useOffline() {
            prefs.edit().putBoolean(K_OFFLINE, true).apply();
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    web.loadUrl("file:///android_asset/index.html");
                }
            });
        }

        @JavascriptInterface
        public void resetServer() {
            prefs.edit().remove(K_SERVER).putBoolean(K_OFFLINE, false).apply();
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    web.loadUrl("file:///android_asset/setup.html");
                }
            });
        }

        @JavascriptInterface
        public void requestLocation() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (hasLocationPermission()) {
                        notifyLocReady();
                    } else {
                        requestPermissions(
                                new String[]{Manifest.permission.ACCESS_FINE_LOCATION,
                                        Manifest.permission.ACCESS_COARSE_LOCATION},
                                REQ_LOCATION);
                    }
                }
            });
        }
    }

    private boolean hasLocationPermission() {
        if (Build.VERSION.SDK_INT < 23) {
            return true;
        }
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    private void notifyLocReady() {
        if (web != null) {
            web.evaluateJavascript(
                    "window.__busanLocReady && window.__busanLocReady();", null);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_LOCATION) {
            // 通过：页面继续取坐标；拒绝：页面展示「定位失败 + 手选出发点」
            notifyLocReady();
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && web != null && web.canGoBack()) {
            web.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}
