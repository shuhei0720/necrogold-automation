import Foundation
import CoreGraphics
import ImageIO

/// Candidate normal-build8 adapter. Runtime keeps the existing11
/// NG2Raster.decodeDetailed -> ng2_analyze_rgba branch byte-for-byte.
enum NG2DeviceRaster {
    enum SourceContract {
        // One original XCT JPEG established these acquired metadata only.
        // This does not qualify freshness, input, motion or the final build.
        case originalPortrait750x1334EXIF8
    }

    struct Decoded {
        // floor is UI-state/beat evidence only; world is the unoverwritten
        // material/signature/Ring proof plane from the SAME original capture.
        let floor: NG2Raster.ProfiledResult
        let world: NG2Raster.ProfiledResult
        let pause: NG2Raster.ProfiledResult
        let floorCoverage: Data
        let worldCoverage: Data
        let worldValidity: NG2ProfileRasterValidity
        let floorValidity: NG2ProfileRasterValidity
        let pauseValidity: NG2ProfileRasterValidity
    }
    struct Selected {
        let raster: NG2Raster.ProfiledResult
        let validity: NG2ProfileRasterValidity
        let view: Int32
        // Actual world support for the same selected FLOOR. PAUSE has no world.
        let floorCoverage: Data?
        // Companion ownership and the existing profile gap31 must travel
        // with this same chosen raster/scene through Runtime publication.
    }
    enum DecodeResult {
        case success(Decoded)
        case failure(NG2Raster.Failure)
    }

    private static func integer(_ value: Any?) -> Int? {
        guard let n = value as? NSNumber, CFGetTypeID(n) != CFBooleanGetTypeID(),
              n.doubleValue.isFinite, n.doubleValue.rounded(.towardZero) == n.doubleValue,
              n.doubleValue >= 0, n.doubleValue <= 4096 else { return nil }
        return n.intValue
    }

    static func decode8(_ encoded: Data, profile: UnsafePointer<NG2DeviceGeometryProfile>,
                        contract: SourceContract?, occlusions: [NG2DeviceRect]) -> DecodeResult {
        let started = DispatchTime.now().uptimeNanoseconds
        var diagnosticWidth: Int?, diagnosticHeight: Int?, diagnosticOrientation: Int?
        func fail(_ stage: NG2Raster.FailureStage, _ code: NG2Raster.FailureCode) -> DecodeResult {
            .failure(.init(stage: stage, code: code, encodedBytes: encoded.count,
                sourceWidth: diagnosticWidth, sourceHeight: diagnosticHeight, orientation: diagnosticOrientation))
        }
        let p = profile.pointee
        guard contract != nil, p.device == 8, p.legacy_passthrough == 0,
              p.panel_width == 375, p.panel_height == 667,
              p.source_point_width == 667, p.source_point_height == 375,
              p.canonical_width == 896, p.canonical_height == 414,
              p.world_to_canonical.a == 1, p.world_to_canonical.b == 0,
              p.world_to_canonical.c == 0, p.world_to_canonical.d == 1,
              p.canonical_source_fov.x0 == p.world_to_canonical.tx,
              p.canonical_source_fov.y0 == p.world_to_canonical.ty,
              p.canonical_source_fov.x1-p.canonical_source_fov.x0 == 667,
              p.canonical_source_fov.y1-p.canonical_source_fov.y0 == 375 else {
            return fail(.metadata, .sourceGeometry)
        }
        guard !encoded.isEmpty else { return fail(.source, .encodedEmpty) }
        guard encoded.count <= 8 * 1024 * 1024 else { return fail(.source, .encodedLimit) }
        guard encoded.starts(with: [255, 216]),
              let source = CGImageSourceCreateWithData(encoded as CFData, nil),
              let type = CGImageSourceGetType(source),
              CFEqual(type, "public.jpeg" as CFString) else { return fail(.source, .sourceOpen) }
        guard CGImageSourceGetCount(source) == 1 else { return fail(.source, .imageCount) }
        let metadata = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
        diagnosticWidth = integer(metadata?[kCGImagePropertyPixelWidth])
        diagnosticHeight = integer(metadata?[kCGImagePropertyPixelHeight])
        diagnosticOrientation = integer(metadata?[kCGImagePropertyOrientation])
        guard diagnosticWidth == 750, diagnosticHeight == 1334 else { return fail(.metadata, .sourceGeometry) }
        guard diagnosticOrientation == 8 else { return fail(.metadata, .orientation) }
        guard let image = CGImageSourceCreateImageAtIndex(source, 0, nil),
              image.width == 750, image.height == 1334 else { return fail(.source, .imageCreate) }
        let sourceEnd = DispatchTime.now().uptimeNanoseconds
        // Reuse the unchanged opaque-sRGB decoder and integer EXIF map at
        // original oriented dimensions. No UIImage or JPEG re-encoding occurs.
        let original: NG2Raster.ProfiledResult
        switch NG2Raster.normalizeDetailed(image, orientation: 8, outputWidth: 1334, outputHeight: 750) {
        case .failure(let f):
            return fail(f.stage, f.code)
        case .success(let value): original = value
        }
        let renderingStart = DispatchTime.now().uptimeNanoseconds
        var floor = Data(count: 896 * 414 * 4), world = Data(count: 896 * 414 * 4)
        var pause = Data(count: 896 * 414 * 4)
        var coverage = Data(count: 896 * 414), worldCoverage = Data(count: 896 * 414)
        var pauseCoverage = Data(count: 896 * 414)
        var fv = NG2ProfileRasterValidity(), wv = NG2ProfileRasterValidity(), pv = NG2ProfileRasterValidity()
        func render(_ view: Int32, _ output: inout Data, _ observed: inout Data,
                    _ validity: inout NG2ProfileRasterValidity) -> Int32 {
            original.rgba.withUnsafeBytes { sourceBytes in
                output.withUnsafeMutableBytes { destination in
                    observed.withUnsafeMutableBytes { support in
                        occlusions.withUnsafeBufferPointer { exclusions in
                            ng2_profile_raster8(sourceBytes.bindMemory(to: UInt8.self).baseAddress,
                                original.rgba.count, 1334, 750, profile, exclusions.baseAddress,
                                exclusions.count, view, destination.bindMemory(to: UInt8.self).baseAddress,
                                896 * 414 * 4, support.bindMemory(to: UInt8.self).baseAddress,
                                896 * 414, &validity)
                        }
                    }
                }
            }
        }
        guard render(Int32(NG2_PROFILE_RASTER_FLOOR), &floor, &coverage, &fv) == 0,
              render(Int32(NG2_PROFILE_RASTER_WORLD), &world, &worldCoverage, &wv) == 0,
              render(Int32(NG2_PROFILE_RASTER_PAUSE), &pause, &pauseCoverage, &pv) == 0 else {
            return fail(.normalize, .renderFailed)
        }
        let trace = NG2Raster.Trace(sourceWidth: 750, sourceHeight: 1334, orientation: 8,
            sourceNs: sourceEnd - started, drawNs: original.trace.drawNs,
            orientNs: original.trace.orientNs,
            scaleNs: DispatchTime.now().uptimeNanoseconds - renderingStart,
            copyPixels: original.trace.copyPixels)
        return .success(Decoded(
            floor: .init(rgba: floor, trace: trace, diagnosticOrientation: 8),
            world: .init(rgba: world, trace: trace, diagnosticOrientation: 8),
            pause: .init(rgba: pause, trace: trace, diagnosticOrientation: 8),
            floorCoverage: coverage, worldCoverage: worldCoverage, worldValidity: wv,
            floorValidity: fv, pauseValidity: pv))
    }

    /// The caller supplies Runtime's heap-owned scene. No large C tuple copy
    /// crosses a Swift stack, and no controller/navigation decision occurs here.
    static func analyze(_ decoded: Decoded, scene: UnsafeMutablePointer<NG2Scene>) -> Selected? {
        var fv = decoded.floorValidity, wv = decoded.worldValidity, pv = decoded.pauseValidity
        var selected = Int32(NG2_PROFILE_RASTER_FLOOR), validity = NG2ProfileRasterValidity()
        let rc = decoded.floor.rgba.withUnsafeBytes { floor in
            decoded.world.rgba.withUnsafeBytes { world in
                decoded.pause.rgba.withUnsafeBytes { pause in
                    decoded.worldCoverage.withUnsafeBytes { coverage in
                        ng2_profile_raster_analyze_world(floor.bindMemory(to: UInt8.self).baseAddress, &fv,
                            world.bindMemory(to: UInt8.self).baseAddress,
                            coverage.bindMemory(to: UInt8.self).baseAddress, &wv,
                            pause.bindMemory(to: UInt8.self).baseAddress, &pv, scene, &selected, &validity)
                    }
                }
            }
        }
        guard rc == 0 else { return nil }
        return Selected(raster: selected == Int32(NG2_PROFILE_RASTER_PAUSE) ? decoded.pause : decoded.world,
                        validity: validity, view: selected,
                        floorCoverage: selected == Int32(NG2_PROFILE_RASTER_FLOOR) ? decoded.worldCoverage : nil)
    }
}
