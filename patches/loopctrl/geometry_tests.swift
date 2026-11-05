// Numerical/selection/closure tests only; does not exercise UIKit or a device.
import Foundation
import CoreGraphics

var passed = 0
func fail(_ name: String, _ message: String) -> Never {
    print("FAIL \(name): \(message)")
    exit(1)
}
func check(_ condition: Bool, _ name: String, _ message: String) {
    if !condition { fail(name, message) }
}
func run(_ name: String, _ body: () throws -> Void) {
    do { try body() } catch { fail(name, "unexpected error \(error)") }
    passed += 1
    print("PASS \(name)")
}
func rejection(_ name: String, code: Int = -32000, _ body: () throws -> Void) {
    do {
        try body()
        fail(name, "expected rejection")
    } catch let failure as NGScreenshotGeometry.Failure {
        check(failure.rpcError.code == code, name, "wrong RPC error")
    } catch { fail(name, "unexpected error \(error)") }
    passed += 1
    print("PASS \(name)")
}
func command(_ extra: [String: JSONValue] = [:]) -> ActionCommand {
    var params: [String: JSONValue] = ["geometry": .string("image_size_v1")]
    for (key, value) in extra { params[key] = value }
    return ActionCommand(method: "screenshot", params: params)
}
func target(_ width: Double = 1792, _ height: Double = 828,
            imageScale: Double = 1, deviceScale: Double = 2,
            scale: Double = 1, mode: NGScreenshotGeometry.Mode = .imageSizeV1) throws -> NGScreenshotGeometry.Target {
    try NGScreenshotGeometry.target(mode: mode, imageSize: CGSize(width: width, height: height),
        imageScale: imageScale, deviceScale: deviceScale, effectiveScale: scale,
        cachedSize: CGSize(width: 414, height: 896))
}
func dimensions(_ name: String, _ width: Double, _ height: Double,
                _ body: () throws -> NGScreenshotGeometry.Target) {
    run(name) {
        let value = try body()
        if value.pixelWidth != width || value.pixelHeight != height {
            fail(name, "expected=\(Int(width))x\(Int(height)) actual=\(Int(value.pixelWidth))x\(Int(value.pixelHeight))")
        }
    }
}

// The first case is the required cached-dimension mutation detector.
dimensions("landscape_scale1", 896, 414) { try target() }
dimensions("landscape_scale2", 1792, 828) { try target(scale: 2) }
dimensions("portrait_scale1", 414, 896) { try target(828, 1792) }
dimensions("uiimage_scale2", 896, 414) { try target(896, 414, imageScale: 2) }
dimensions("device_scale3", 896, 414) { try target(2688, 1242, deviceScale: 3) }
dimensions("uiimage2_device3_scale2", 1792, 828) { try target(1344, 621, imageScale: 2, deviceScale: 3, scale: 2) }
dimensions("square_scale3", 1200, 1200) { try target(1200, 1200, deviceScale: 3, scale: 3) }
dimensions("legacy_landscape_stays_cached", 414, 896) { try target(mode: .legacy) }
dimensions("legacy_scale2_stays_cached", 828, 1792) { try target(scale: 2, mode: .legacy) }
dimensions("legacy_fractional_metadata_unchanged", 20.700000000000003, 44.800000000000004) { try target(scale: 0.05, mode: .legacy) }
dimensions("eight_million_exact", 4000, 2000) { try target(4000, 2000, deviceScale: 1) }
dimensions("axis_4096_exact", 4096, 1000) { try target(4096, 1000, deviceScale: 1) }
dimensions("one_pixel_exact", 1, 1) { try target(1, 1, deviceScale: 1) }
dimensions("positive_half_rounds_up", 101, 201) { try target(100.5, 200.5, deviceScale: 1) }
rejection("raw_axis_over_bound") { _ = try target(4096.01, 100, deviceScale: 1) }
rejection("raw_area_over_bound") { _ = try target(4000.1, 2000, deviceScale: 1) }
rejection("rounded_area_over_bound") { _ = try target(4000.6, 1999.6, deviceScale: 1) }
rejection("raw_axis_below_one") { _ = try target(0.6, 100, deviceScale: 1) }
for (name, invalid) in [("zero", 0.0), ("negative", -1.0), ("nan", Double.nan),
                        ("infinity", Double.infinity), ("negative_infinity", -Double.infinity)] {
    rejection("image_width_\(name)") { _ = try target(invalid, 828) }
    rejection("image_height_\(name)") { _ = try target(1792, invalid) }
    rejection("image_scale_\(name)") { _ = try target(imageScale: invalid) }
    rejection("device_scale_\(name)") { _ = try target(deviceScale: invalid) }
    rejection("effective_scale_\(name)") { _ = try target(scale: invalid) }
}
rejection("derived_overflow") { _ = try target(Double.greatestFiniteMagnitude, 100, imageScale: 2) }
rejection("source_pixel_overflow") { _ = try target(Double.greatestFiniteMagnitude, 100, imageScale: 2, deviceScale: Double.greatestFiniteMagnitude) }
run("default_scale_and_mode") {
    let selected = try NGScreenshotGeometry.request(command())
    check(selected.mode == .imageSizeV1 && selected.requestedScale == 2 && selected.effectiveScale == 2,
          "default_scale_and_mode", "wrong selection")
}
run("omitted_geometry_legacy") {
    let selected = try NGScreenshotGeometry.request(ActionCommand(method: "screenshot", params: nil))
    check(selected.mode == .legacy, "omitted_geometry_legacy", "wrong selection")
}
run("legacy_bundle_id_remains_allowed") {
    let selected = try NGScreenshotGeometry.request(ActionCommand(method: "screenshot", params: ["bundle_id": .string("test.app")]))
    check(selected.mode == .legacy, "legacy_bundle_id_remains_allowed", "wrong selection")
}
for (label, value) in [("zero", 0.0), ("negative", -4.0), ("low", 0.04), ("min", 0.05), ("one", 1.0), ("two", 2.0), ("three", 3.0), ("high", 4.0)] {
    run("requested_scale_\(label)") {
        let selected = try NGScreenshotGeometry.request(command(["scale": .double(value)]))
        let expected = value < 0.05 ? 0.05 : (value > 3 ? 3 : value)
        check(selected.requestedScale == value && selected.effectiveScale == expected, "requested_scale_\(label)", "wrong clamp")
    }
}
for value in [Double.nan, Double.infinity, -Double.infinity] {
    rejection("nonfinite_requested_scale_\(value)", code: -32602) {
        _ = try NGScreenshotGeometry.request(command(["scale": .double(value)]))
    }
}
let malformed: [(String, JSONValue)] = [("null", .null), ("empty", .string("")), ("unknown", .string("bad")),
    ("int", .int(1)), ("double", .double(1.2)), ("bool", .bool(true)), ("array", .array([])), ("object", .object([:]))]
for (name, value) in malformed {
    rejection("geometry_rejects_\(name)", code: -32602) {
        _ = try NGScreenshotGeometry.request(command(["geometry": value]))
    }
    rejection("bundle_presence_rejects_\(name)", code: -32602) {
        _ = try NGScreenshotGeometry.request(command(["bundle_id": value]))
    }
}
rejection("bundle_presence_rejects_valid_id", code: -32602) {
    _ = try NGScreenshotGeometry.request(command(["bundle_id": .string("test.app")]))
}
for (name, value) in malformed where value.doubleValue == nil {
    rejection("scale_rejects_\(name)", code: -32602) {
        _ = try NGScreenshotGeometry.request(command(["scale": value]))
    }
}
run("json_decoder_preserves_explicit_null") {
    let wire = Data(#"{"jsonrpc":"2.0","method":"screenshot","params":{"geometry":null},"id":1}"#.utf8)
    let decoded = try JSONDecoder().decode(JSONRPCRequest.self, from: wire)
    let parsed = ActionCommand(method: decoded.method, params: decoded.params)
    check(parsed.geometry == .null, "json_decoder_preserves_explicit_null", "null was lost")
}
for format in ["jpeg", "png"] {
    for empty in [false, true] {
        var calls = 0
        rejection("\(format)_\(empty ? "empty" : "nil")_encoding") {
            _ = try NGScreenshotGeometry.encode { calls += 1; return empty ? Data() : nil }
        }
        check(calls == 1, "single_encoding_attempt", "encoder called \(calls) times")
    }
    run("\(format)_nonempty_encoding") {
        var calls = 0
        let expected = Data([1, 2, 3])
        let actual = try NGScreenshotGeometry.encode { calls += 1; return expected }
        check(actual == expected && calls == 1, "nonempty_encoding", "wrong bytes or repeated call")
    }
}
for home in [false, true] {
    run("final_warning_home_\(home)") {
        var response: [String: JSONValue] = ["point_width": .double(414), "point_height": .double(896),
            "scope": .string("screen"), "hint": .string(home ? "Home Screen advice" : "legacy conversion")]
        let value = try target()
        NGScreenshotGeometry.annotate(&response, target: value, sourceSize: CGSize(width: 1792, height: 828),
                                      sourceScale: 1, sourceOrientation: 3)
        check(response["input_geometry_verified"] == .bool(false), "final_warning", "missing false flag")
        check(response["hint"]?.stringValue?.contains("NOT been verified") == true, "final_warning", "warning overwritten")
        check(response["point_width"] == .double(414) && response["point_height"] == .double(896), "final_warning", "input report changed")
        check(response["image_point_width"] == .double(896) && response["image_point_height"] == .double(414), "final_warning", "image points wrong")
        check(response["source_width"] == .double(1792) && response["source_height"] == .double(828)
            && response["source_pixel_width"] == .double(1792) && response["source_pixel_height"] == .double(828)
            && response["source_scale"] == .double(1) && response["source_orientation"] == .int(3), "final_warning", "source metadata wrong")
        check(response["geometry"] == .string("image_size_v1") && response["scope"] == .string("screen"), "final_warning", "scope/mode wrong")
    }
}
print("PASS all \(passed) pure Swift contracts; UIKit/device not executed")
