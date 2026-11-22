import UIKit
import WebKit
import CoreLocation

/// iOS 壳：WKWebView 加载与 Android 完全相同的 assets/index.html，
/// 并补齐网页需要的 BusanHost 桥（取网络文本、定位授权与坐标回传、打开系统设置）。
final class BusanViewController: UIViewController, WKScriptMessageHandler, WKUIDelegate,
    WKNavigationDelegate, CLLocationManagerDelegate {

    private var webView: WKWebView!
    private let locationManager = CLLocationManager()
    private var watching = false

    /// 注入到网页的桥：与 Android 的 @JavascriptInterface 同名同参数，网页侧无需分支。
    private static let bridgeJS = """
    (function(){
      if (window.BusanHost && window.BusanHost.__ios) return;
      function post(o){ try { window.webkit.messageHandlers.busan.postMessage(o); } catch (e) {} }
      window.__busanLocAuth = window.__busanLocAuth || "prompt";
      window.BusanHost = {
        __ios: true,
        fetchText: function(url, id){ post({cmd:"fetchText", url:String(url), id:String(id)}); },
        requestLocation: function(){ post({cmd:"requestLocation"}); },
        hasLocationPermission: function(){ return window.__busanLocAuth === "granted"; },
        startLocationWatch: function(){ post({cmd:"startWatch"}); return true; },
        stopLocationWatch: function(){ post({cmd:"stopWatch"}); },
        openAppSettings: function(){ post({cmd:"settings"}); },
        netAllowed: function(){ return true; }
      };
    })();
    """

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = UIColor(red: 0.965, green: 0.945, blue: 0.906, alpha: 1)

        let config = WKWebViewConfiguration()
        config.allowsInlineMediaPlayback = true
        config.setValue(true, forKey: "allowFileAccessFromFileURLs")
        config.setValue(true, forKey: "allowUniversalAccessFromFileURLs")

        let controller = WKUserContentController()
        controller.add(self, name: "busan")
        controller.addUserScript(WKUserScript(source: BusanViewController.bridgeJS,
                                              injectionTime: .atDocumentStart,
                                              forMainFrameOnly: true))
        config.userContentController = controller

        webView = WKWebView(frame: view.bounds, configuration: config)
        webView.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        view.addSubview(webView)

        locationManager.delegate = self
        locationManager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        locationManager.distanceFilter = 12

        loadAssets()
        pushAuthState()
    }

    private func loadAssets() {
        guard let index = Bundle.main.url(forResource: "index", withExtension: "html", subdirectory: "assets") else {
            let alert = UILabel(frame: view.bounds)
            alert.text = "assets/index.html 未打包进来：请先运行 xcodegen generate 再编译。"
            alert.numberOfLines = 0
            alert.textAlignment = .center
            view.addSubview(alert)
            return
        }
        webView.loadFileURL(index, allowingReadAccessTo: index.deletingLastPathComponent())
    }

    // MARK: - 定位

    private func authString(_ status: CLAuthorizationStatus) -> String {
        switch status {
        case .authorizedAlways, .authorizedWhenInUse: return "granted"
        case .denied, .restricted: return "denied"
        default: return "prompt"
        }
    }

    private func pushAuthState() {
        let state = authString(locationManager.authorizationStatus)
        webView.evaluateJavaScript("window.__busanLocAuth = \(jsLiteral(state));") { _, _ in }
    }

    private func sendLocation(_ location: CLLocation) {
        let ms = Int(Date().timeIntervalSince1970 * 1000)
        let js = "window.__busanLocUpdate && window.__busanLocUpdate(\(location.coordinate.latitude), " +
            "\(location.coordinate.longitude), \(location.horizontalAccuracy), 'gps', \(ms));"
        DispatchQueue.main.async { [weak self] in self?.webView.evaluateJavaScript(js) { _, _ in } }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        if let last = locations.last { sendLocation(last) }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        let denied = (error as? CLError)?.code == .denied
        let js = "window.__busanLocError && window.__busanLocError(\(denied ? 1 : 2), '');"
        DispatchQueue.main.async { [weak self] in self?.webView.evaluateJavaScript(js) { _, _ in } }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        pushAuthState()
        if watching && authString(manager.authorizationStatus) == "granted" {
            manager.startUpdatingLocation()
        }
    }

    // MARK: - JS 消息

    func userContentController(_ userContentController: WKUserContentController,
                               didReceive message: WKScriptMessage) {
        guard let body = message.body as? [String: Any], let cmd = body["cmd"] as? String else { return }
        switch cmd {
        case "fetchText":
            let url = (body["url"] as? String) ?? ""
            let ident = (body["id"] as? String) ?? ""
            fetchText(url: url, id: ident)
        case "requestLocation":
            locationManager.requestWhenInUseAuthorization()
            locationManager.requestLocation()
        case "startWatch":
            watching = true
            if locationManager.authorizationStatus == .notDetermined {
                locationManager.requestWhenInUseAuthorization()
            }
            locationManager.startUpdatingLocation()
        case "stopWatch":
            watching = false
            locationManager.stopUpdatingLocation()
        case "settings":
            if let url = URL(string: UIApplication.openSettingsURLString) {
                UIApplication.shared.open(url)
            }
        default:
            break
        }
    }

    private func fetchText(url: String, id: String) {
        guard let target = URL(string: url) else {
            notifyHttp(id: id, status: -1, body: "")
            return
        }
        var request = URLRequest(url: target)
        request.timeoutInterval = 20
        request.cachePolicy = .reloadIgnoringLocalCacheData
        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            let status = (response as? HTTPURLResponse)?.statusCode ?? (error == nil ? 200 : -1)
            let text = data.flatMap { String(data: $0, encoding: .utf8) } ?? ""
            DispatchQueue.main.async {
                self?.notifyHttp(id: id, status: status, body: text)
            }
        }.resume()
    }

    private func notifyHttp(id: String, status: Int, body: String) {
        let js = "window.__busanHttpDone && window.__busanHttpDone(\(jsLiteral(id)), \(status), \(jsLiteral(body)));"
        webView.evaluateJavaScript(js) { _, _ in }
    }

    /// 生成 JSON 字符串字面量（含引号），避免把接口返回的换行/引号拼坏。
    private func jsLiteral(_ value: String) -> String {
        if let data = try? JSONSerialization.data(withJSONObject: [value], options: []),
           let raw = String(data: data, encoding: .utf8) {
            return String(raw.dropFirst().dropLast())
        }
        return "\"\""
    }

    // MARK: - 导航与外部链接

    func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }
        if url.isFileURL || url.scheme == "about" {
            decisionHandler(.allow)
            return
        }
        if navigationAction.navigationType == .linkActivated {
            UIApplication.shared.open(url, options: [:], completionHandler: nil)
            decisionHandler(.cancel)
            return
        }
        decisionHandler(.allow)
    }
}
