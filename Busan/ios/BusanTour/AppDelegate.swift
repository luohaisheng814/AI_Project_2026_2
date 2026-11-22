import UIKit

@main
final class AppDelegate: UIResponder, UIApplicationDelegate {

    var window: UIWindow?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = BusanViewController()
        window.backgroundColor = UIColor(red: 0.965, green: 0.945, blue: 0.906, alpha: 1)
        window.makeKeyAndVisible()
        self.window = window
        return true
    }
}
