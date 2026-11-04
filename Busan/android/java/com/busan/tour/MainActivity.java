package com.busan.tour;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.view.KeyEvent;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * 独立安装包的壳：只做一件事——把安装包内置的离线网页加载进 WebView。
 * 网页里已经带着完整的中文数据库与韩 / 英预翻译正文，所以不需要联网、
 * 不需要连接电脑上的服务，点开就能问。
 *
 * 定位：Android 6 起「声明权限」不等于「拿到权限」，必须在运行时请求，
 * 否则 navigator.geolocation 一律回调 PERMISSION_DENIED，页面只会显示
 * 「定位不可用」。这里补上运行时请求，并给网页一个 BusanHost 桥，
 * 让「附近」按钮可以先弹系统授权框，授权通过后再取坐标。
 */
public class MainActivity extends Activity {

    private static final int REQ_LOCATION = 1001;

    private WebView web;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        web = new WebView(this);
        setContentView(web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true);
        s.setGeolocationEnabled(true);
        s.setTextZoom(100);

        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                // 非 http(s) 的外部跳转（如 naver 地图 scheme）交回系统处理
                if (url != null && (url.startsWith("http://") || url.startsWith("https://"))) {
                    view.loadUrl(url);
                    return true;
                }
                return false;
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onGeolocationPermissionsShowPrompt(String origin,
                                                           GeolocationPermissions.Callback callback) {
                // 定位只用于「附近景点」排序，直接授予但不长期保存
                callback.invoke(origin, true, false);
            }
        });

        web.addJavascriptInterface(new LocationBridge(), "BusanHost");
        web.loadUrl("file:///android_asset/index.html");
    }

    /** 网页侧调用入口：需要定位时先走系统运行时授权，拿到后回调 __busanLocReady。 */
    private class LocationBridge {
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
            // 无论通过还是拒绝，都让网页继续：通过则取坐标，拒绝则页面给出提示
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
