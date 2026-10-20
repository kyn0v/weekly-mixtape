// Bounded accessibility helper. Paths/coordinates must come from the current UI.
import AppKit
import ApplicationServices

func fail(_ text: String) -> Never { fputs(text + "\n", stderr); exit(1) }
let args = Array(CommandLine.arguments.dropFirst())
guard AXIsProcessTrusted() else { fail("Accessibility permission required") }
let bundle = ProcessInfo.processInfo.environment["AX_BUNDLE"] ?? "com.apple.garageband10"
guard let process = NSRunningApplication.runningApplications(withBundleIdentifier: bundle).first else { fail("Target app is not running: \(bundle)") }
let app = AXUIElementCreateApplication(process.processIdentifier)
func activate() {
    process.activate(options: []); usleep(700000)
    guard NSWorkspace.shared.frontmostApplication?.bundleIdentifier == bundle else { fail("Target app is not frontmost") }
}
func get(_ e: AXUIElement, _ key: String) -> CFTypeRef? {
    var v: CFTypeRef?; guard AXUIElementCopyAttributeValue(e, key as CFString, &v) == .success else { return nil }; return v
}
func children(_ e: AXUIElement) -> [AXUIElement] {
    (get(e, "AXChildren") as? [AXUIElement] ?? []).filter { (get($0, "AXRole") as? String) != "AXHelpTag" }
}
func node(_ path: String) -> AXUIElement {
    var e = app
    for part in path.split(separator: ".") {
        guard let i = Int(part), children(e).indices.contains(i) else { fail("Stale/invalid AX path: \(path)") }
        e = children(e)[i]
    }
    return e
}
func describe(_ e: AXUIElement) -> String {
    ["AXRole", "AXTitle", "AXDescription", "AXValue", "AXHelp", "AXPosition", "AXSize"].compactMap { k in get(e,k).map { "\(k)=\($0)" } }.joined(separator:" | ")
}
func dump(_ e: AXUIElement, _ path: String, _ depth: Int) {
    print(path + " " + describe(e))
    if depth > 0 { for (i,c) in children(e).enumerated() { dump(c, path.isEmpty ? "\(i)" : "\(path).\(i)", depth-1) } }
}
func check(_ result: AXError) { if result != .success { fail("AX error: \(result.rawValue)") } }
func rect(_ e: AXUIElement) -> CGRect {
    guard let p = get(e,"AXPosition"), let s = get(e,"AXSize") else { fail("Element has no geometry") }
    var point = CGPoint.zero; var size = CGSize.zero
    guard AXValueGetValue(p as! AXValue,.cgPoint,&point), AXValueGetValue(s as! AXValue,.cgSize,&size) else { fail("Invalid geometry") }
    return CGRect(origin: point, size: size)
}
func mouse(_ type: CGEventType, _ point: CGPoint, _ clicks: Int64 = 1) {
    guard let event = CGEvent(mouseEventSource:nil,mouseType:type,mouseCursorPosition:point,mouseButton:.left) else { fail("Cannot create event") }
    event.flags = []; event.setIntegerValueField(.mouseEventClickState,value:clicks); event.post(tap:.cghidEventTap)
}
func visible(_ point: CGPoint) {
    guard let window = children(app).first(where: { get($0,"AXRole") as? String == "AXWindow" }), rect(window).contains(point), point.y > 110 else { fail("Scroll target into view first") }
}
guard let command = args.first else { fail("dump [path] [depth] | attrs path | action path action | set path key type value | click path | doubleclick path | dragToTrack region track | fileClipboard file | textClipboard text | focused | setFocusedText text") }
switch command {
case "dump":
    let path = args.count > 1 ? args[1] : ""
    let depth = args.count > 2 ? Int(args[2]) ?? 2 : 2
    dump(node(path),path,min(8,max(0,depth)))
case "attrs":
    let e = node(args[1]); var names: CFArray?; check(AXUIElementCopyAttributeNames(e,&names))
    for k in names as? [String] ?? [] { var settable: DarwinBoolean = false; AXUIElementIsAttributeSettable(e,k as CFString,&settable); print(k,"settable",settable,"value",get(e,k) as Any) }
    var acts: CFArray?; AXUIElementCopyActionNames(e,&acts); print("Actions",acts as Any)
case "action": check(AXUIElementPerformAction(node(args[1]), args[2] as CFString))
case "repeatAction":
    guard args.count == 4, let count = Int(args[3]), (1...5000).contains(count) else { fail("Expected action and count 1...5000") }
    let e = node(args[1]); for _ in 0..<count { check(AXUIElementPerformAction(e,args[2] as CFString)) }
    print(describe(e)); print("Value description:",get(e,"AXValueDescription") as Any)
case "set":
    let value: CFTypeRef
    if args[3] == "number" { guard let n = Double(args[4]) else { fail("Invalid number") }; value = NSNumber(value:n) }
    else if args[3] == "bool" { value = NSNumber(value:args[4] == "true") }
    else { value = args[4] as CFString }
    check(AXUIElementSetAttributeValue(node(args[1]),args[2] as CFString,value))
case "clickAt", "rightclickAt":
    activate()
    guard args.count == 3, let x = Double(args[1]), let y = Double(args[2]) else { fail("Expected x y in screen points") }
    let p = CGPoint(x:x,y:y); visible(p)
    let right = command == "rightclickAt"
    for type in right ? [CGEventType.rightMouseDown,.rightMouseUp] : [CGEventType.leftMouseDown,.leftMouseUp] {
        guard let e = CGEvent(mouseEventSource:nil,mouseType:type,mouseCursorPosition:p,mouseButton:right ? .right : .left) else { fail("Cannot create event") }
        e.flags = []; e.post(tap:.cghidEventTap); usleep(70000)
    }
case "click", "doubleclick":
    activate()
    let r = rect(node(args[1])); let p = CGPoint(x:r.midX,y:r.midY)
    // Also allows transport/display controls, but rejects off-window elements.
    guard let w = children(app).first(where:{ get($0,"AXRole") as? String == "AXWindow" }), rect(w).contains(p) else { fail("Target not visible") }
    for n in 1...(command == "doubleclick" ? 2 : 1) { mouse(.leftMouseDown,p,Int64(n)); mouse(.leftMouseUp,p,Int64(n)); usleep(80000) }
case "dragToTrack", "dragBy":
    activate()
    let r = rect(node(args[1]))
    let a = CGPoint(x:r.midX,y:r.midY)
    let b: CGPoint
    if command == "dragToTrack" { b = CGPoint(x:r.midX,y:rect(node(args[2])).midY) }
    else { guard args.count == 4, let dx = Double(args[2]), let dy = Double(args[3]) else { fail("Expected dx dy") }; b = CGPoint(x:a.x+dx,y:a.y+dy) }
    visible(a); visible(b); mouse(.leftMouseDown,a); usleep(200000)
    for i in 1...20 { mouse(.leftMouseDragged,CGPoint(x:a.x+(b.x-a.x)*Double(i)/20,y:a.y+(b.y-a.y)*Double(i)/20)); usleep(30000) }
    mouse(.leftMouseUp,b); usleep(300000)
case "fileClipboard":
    let path = (args[1] as NSString).expandingTildeInPath
    guard FileManager.default.fileExists(atPath:path) else { fail("Missing clipboard file") }
    let board = NSPasteboard.general
    board.clearContents()
    guard board.setString(URL(fileURLWithPath:path).absoluteString,forType:.fileURL), board.setPropertyList([path],forType:NSPasteboard.PasteboardType("NSFilenamesPboardType")) else { fail("Clipboard failed") }
case "textClipboard": NSPasteboard.general.clearContents(); NSPasteboard.general.setString(args[1],forType:.string)
case "focused", "setFocusedText":
    guard let v = get(app,"AXFocusedUIElement") else { fail("No focused element") }; let e = v as! AXUIElement
    if command == "focused" { print(describe(e)) }
    else { guard get(e,"AXRole") as? String == "AXTextField" else { fail("Focus is not a text field") }; check(AXUIElementSetAttributeValue(e,"AXValue" as CFString,args[1] as CFString)) }
default: fail("Unknown command")
}
