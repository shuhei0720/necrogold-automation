// A self-owned AppKit window and an independent, PID-addressed event sender.
// No permission requests, account queries, or whole-screen capture APIs.
import AppKit
import CoreGraphics
import Darwin
import Dispatch
import Foundation
import Metal

func emit(_ object: [String: Any]) {
    if let data = try? JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data([10]))
    }
}

func argument(_ name: String) -> String? {
    guard let index = CommandLine.arguments.firstIndex(of: name),
          index + 1 < CommandLine.arguments.count else { return nil }
    return CommandLine.arguments[index + 1]
}

func loadState(_ path: String) -> [String: Any]? {
    guard let data = try? Data(contentsOf: URL(fileURLWithPath: path)),
          let value = try? JSONSerialization.jsonObject(with: data) else { return nil }
    return value as? [String: Any]
}

func ownership(pid: Int32, windowID: CGWindowID, statePath: String, nonce: String) -> [String: Any] {
    let state = loadState(statePath)
    let age = Date().timeIntervalSince1970 - ((state?["updated_unix"] as? Double) ?? 0)
    let alive = pid > 0 && kill(pid, 0) == 0
    let nonceMatches = state?["nonce"] as? String == nonce && !nonce.isEmpty
    let stateMatches = (state?["pid"] as? Int) == Int(pid)
        && (state?["window_id"] as? Int) == Int(windowID)
    let fresh = age >= -1 && age <= 3
    let windows = CGWindowListCopyWindowInfo(.optionIncludingWindow, windowID) as? [[String: Any]]
    let ownWindow = windows?.contains {
        ($0[kCGWindowNumber as String] as? Int) == Int(windowID)
            && ($0[kCGWindowOwnerPID as String] as? Int) == Int(pid)
    } ?? false
    let frontmost = NSWorkspace.shared.frontmostApplication?.processIdentifier == pid
    return ["alive": alive, "nonce_matches": nonceMatches, "state_matches": stateMatches,
            "state_fresh": fresh, "window_owner_matches": ownWindow,
            "frontmost_matches": frontmost,
            "owned": alive && nonceMatches && stateMatches && fresh && ownWindow]
}

func requestedOwnership() -> [String: Any]? {
    guard let rawPID = argument("--pid"), let pid = Int32(rawPID),
          let rawWindow = argument("--window-id"), let window = UInt32(rawWindow), window > 0,
          let state = argument("--state"), let nonce = argument("--nonce") else { return nil }
    return ownership(pid: pid, windowID: window, statePath: state, nonce: nonce)
}

func capabilities() {
    // Inspection mode returns only the requested window's ownership booleans.
    if argument("--pid") != nil {
        emit(["status": "observed", "ownership": requestedOwnership() ?? ["owned": false]])
        return
    }
    let version = ProcessInfo.processInfo.operatingSystemVersion
    let devices = MTLCopyAllDevices()
    var system = utsname()
    uname(&system)
    let machineCapacity = MemoryLayout.size(ofValue: system.machine)
    let architecture = withUnsafePointer(to: &system.machine) {
        $0.withMemoryRebound(to: CChar.self, capacity: machineCapacity) {
            String(cString: $0)
        }
    }
    emit([
        "status": "observed", "architecture": architecture,
        "monotonic_ns": DispatchTime.now().uptimeNanoseconds,
        "macos_version": "\(version.majorVersion).\(version.minorVersion).\(version.patchVersion)",
        "metal_device_count": devices.count, "metal_device_names": devices.map { $0.name },
        "metal_command_execution_tested": false, "screen_count": NSScreen.screens.count,
        "screen_capture_preflight": CGPreflightScreenCaptureAccess(),
        "post_event_preflight": CGPreflightPostEventAccess(),
        "app_store_present": ["/System/Applications/App Store.app", "/Applications/App Store.app"]
            .contains { FileManager.default.fileExists(atPath: $0) }
    ])
}

final class ProbeView: NSView {
    var keyDownCount = 0
    var keyUpCount = 0
    var drawCount = 0
    var lastDrawColor = "none"
    var changed: (() -> Void)?
    override var acceptsFirstResponder: Bool { true }
    override func draw(_ dirtyRect: NSRect) {
        (keyDownCount == 0 ? NSColor.red : NSColor.blue).setFill()
        bounds.fill()
        drawCount += 1
        lastDrawColor = keyDownCount == 0 ? "red" : "blue"
        changed?()
    }
    override func keyDown(with event: NSEvent) {
        guard event.keyCode == 49, !event.isARepeat else { return }
        keyDownCount += 1
        needsDisplay = true
        changed?()
    }
    override func keyUp(with event: NSEvent) {
        guard event.keyCode == 49 else { return }
        keyUpCount += 1
        changed?()
    }
}

final class ProbeDelegate: NSObject, NSApplicationDelegate {
    let statePath: String
    let nonce: String
    var window: NSWindow?
    let view = ProbeView(frame: NSRect(x: 0, y: 0, width: 400, height: 240))
    init(statePath: String, nonce: String) { self.statePath = statePath; self.nonce = nonce }
    func save() {
        guard let window = window else { return }
        let state: [String: Any] = [
            "pid": Int(getpid()), "window_id": window.windowNumber, "nonce": nonce,
            "updated_unix": Date().timeIntervalSince1970,
            "key_down_count": view.keyDownCount, "key_up_count": view.keyUpCount,
            "draw_count": view.drawCount, "last_draw_color": view.lastDrawColor,
            "is_key_window": window.isKeyWindow,
            "frontmost_matches": NSWorkspace.shared.frontmostApplication?.processIdentifier == getpid(),
            "content_width_pt": 400, "content_height_pt": 240
        ]
        if let data = try? JSONSerialization.data(withJSONObject: state, options: [.sortedKeys]) {
            try? data.write(to: URL(fileURLWithPath: statePath), options: .atomic)
        }
    }
    func applicationDidFinishLaunching(_ notification: Notification) {
        let window = NSWindow(contentRect: view.bounds, styleMask: [.titled, .closable],
                              backing: .buffered, defer: false)
        self.window = window
        window.title = "CI Capability Probe"
        window.contentView = view
        window.setFrameOrigin(NSPoint(x: 80, y: 80))
        window.isReleasedWhenClosed = false
        view.changed = { [weak self] in self?.save() }
        window.makeKeyAndOrderFront(nil)
        window.makeFirstResponder(view)
        NSApp.activate(ignoringOtherApps: true)
        view.needsDisplay = true
        window.displayIfNeeded()
        save()
        Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in self?.save() }
        // Independent safety bound, even if the Python parent disappears.
        Timer.scheduledTimer(withTimeInterval: 90, repeats: false) { _ in NSApp.terminate(nil) }
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
}

func send() {
    guard let rawPID = argument("--pid"), let pid = Int32(rawPID),
          let rawWindow = argument("--window-id"), let window = UInt32(rawWindow),
          let path = argument("--state"), let nonce = argument("--nonce"),
          let pendingPath = argument("--pending"),
          let rawDeadline = argument("--deadline-ns"), let deadline = UInt64(rawDeadline) else {
        emit(["status": "blocked", "reason": "invalid_target"]); return
    }
    var report: [String: Any] = ["status": "blocked", "key_down_posted": false,
                               "key_up_posted": false, "method": "CGEvent.postToPid"]
    let upOnly = CommandLine.arguments.contains("--key-up-only")
    report["mode"] = upOnly ? "key_up_only" : "key_pair"
    func pending(_ needed: Bool) -> Bool {
        let record: [String: Any] = ["pid": Int(pid), "window_id": Int(window),
                                   "nonce": nonce, "pending_key_up": needed]
        guard let data = try? JSONSerialization.data(withJSONObject: record, options: [.sortedKeys]) else {
            return false
        }
        do { try data.write(to: URL(fileURLWithPath: pendingPath), options: .atomic); return true }
        catch { return false }
    }
    if upOnly {
        let record = loadState(pendingPath)
        guard record?["pending_key_up"] as? Bool == true,
              record?["nonce"] as? String == nonce, record?["pid"] as? Int == Int(pid),
              record?["window_id"] as? Int == Int(window) else {
            report["reason"] = "no_matching_pending_key_up"; emit(report); return
        }
    }
    guard CGPreflightPostEventAccess() else {
        report["reason"] = "post_event_preflight_false"
        emit(report); return
    }
    let before = ownership(pid: pid, windowID: window, statePath: path, nonce: nonce)
    report["ownership_before"] = before
    guard before["owned"] as? Bool == true,
          upOnly || before["frontmost_matches"] as? Bool == true else {
        report["reason"] = "target_not_owned_and_frontmost"; emit(report); return
    }
    guard let source = CGEventSource(stateID: .privateState),
          let down = CGEvent(keyboardEventSource: source, virtualKey: 49, keyDown: true),
          let up = CGEvent(keyboardEventSource: source, virtualKey: 49, keyDown: false) else {
        report["reason"] = "event_creation_failed"; emit(report); return
    }
    if upOnly {
        // Cleanup can only release a pending key to its verified original owner.
        let current = ownership(pid: pid, windowID: window, statePath: path, nonce: nonce)
        guard current["owned"] as? Bool == true, DispatchTime.now().uptimeNanoseconds < deadline else {
            report["reason"] = "cleanup_owner_or_deadline_invalid"; emit(report); return
        }
        up.postToPid(pid)
        report["key_up_posted"] = true
        report["pending_cleared"] = pending(false)
        report["status"] = "released"
        emit(report); return
    }
    guard DispatchTime.now().uptimeNanoseconds < deadline else {
        report["reason"] = "deadline_before_key_down"; emit(report); return
    }
    // Recheck immediately before each event. Never send to the global event tap.
    let immediate = ownership(pid: pid, windowID: window, statePath: path, nonce: nonce)
    guard immediate["owned"] as? Bool == true, immediate["frontmost_matches"] as? Bool == true,
          DispatchTime.now().uptimeNanoseconds < deadline else {
        report["reason"] = "target_changed_before_key_down"; emit(report); return
    }
    // Durable intent is recorded first: a killed sender can then be released by the parent.
    guard pending(true) else {
        report["reason"] = "pending_record_failed"; emit(report); return
    }
    let ready = ownership(pid: pid, windowID: window, statePath: path, nonce: nonce)
    guard ready["owned"] as? Bool == true, ready["frontmost_matches"] as? Bool == true,
          DispatchTime.now().uptimeNanoseconds < deadline else {
        _ = pending(false)
        report["reason"] = "owner_or_deadline_changed_after_pending_record"; emit(report); return
    }
    down.postToPid(pid)
    report["key_down_posted"] = true
    let afterDown = ownership(pid: pid, windowID: window, statePath: path, nonce: nonce)
    if afterDown["owned"] as? Bool == true {
        up.postToPid(pid)
        report["key_up_posted"] = true
        report["pending_cleared"] = pending(false)
        report["status"] = "posted"
    } else {
        report["reason"] = "ownership_lost_before_key_up"
    }
    report["ownership_after_down"] = afterDown
    emit(report)
}

switch CommandLine.arguments.dropFirst().first {
case "capabilities": capabilities()
case "send": send()
case "app":
    guard let path = argument("--state"), let nonce = argument("--nonce"), !nonce.isEmpty else { exit(2) }
    let app = NSApplication.shared
    let delegate = ProbeDelegate(statePath: path, nonce: nonce)
    app.setActivationPolicy(.regular)
    app.delegate = delegate
    withExtendedLifetime(delegate) { app.run() }
default: emit(["status": "error", "reason": "unknown_mode"]); exit(2)
}
