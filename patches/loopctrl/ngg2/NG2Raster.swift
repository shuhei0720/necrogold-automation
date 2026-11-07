import Foundation
import CoreGraphics
import ImageIO

enum NG2Raster {
    static let width = 896
    static let height = 414
    static let stride = width * 4

    /// ImageIO may defer JPEG decompression until the opaque draw. The source
    /// stage therefore measures source/image creation, not JPEG decoding alone.
    struct Trace {
        let sourceWidth: Int
        let sourceHeight: Int
        let orientation: Int
        let sourceNs: UInt64
        let drawNs: UInt64
        let orientNs: UInt64
        let scaleNs: UInt64
        let copyPixels: UInt64
    }

    struct ProfiledResult {
        let rgba: Data
        let trace: Trace
        // The effective processing orientation may be default 1 even when
        // ImageIO supplied no EXIF value. Keep acquired metadata separate.
        let diagnosticOrientation: Int?
    }

    enum FailureStage: String {
        case interval, reply, source, metadata, normalize, analysis
    }

    enum FailureCode: String {
        case invalidInterval = "invalid_interval"
        case apiUnavailable = "api_unavailable"
        case sessionUnavailable = "session_unavailable"
        case displayUnprepared = "display_unprepared"
        case requestUnavailable = "request_unavailable"
        case captureFailed = "capture_failed"
        case bytesInvalid = "bytes_invalid"
        case replyException = "reply_exception"
        case requestException = "request_exception"
        case missingData = "missing_data"
        case other
        case encodedEmpty = "encoded_empty"
        case encodedLimit = "encoded_limit"
        case sourceOpen = "source_open"
        case imageCount = "image_count"
        case imageCreate = "image_create"
        case orientation
        case sourceGeometry = "source_geometry"
        case aspect
        case renderFailed = "render_failed"
        case orientationCopy = "orientation_copy"
        case invalidRGBA = "invalid_rgba"
    }

    struct Failure {
        let stage: FailureStage
        let code: FailureCode
        let encodedBytes: Int?
        let sourceWidth: Int?
        let sourceHeight: Int?
        let orientation: Int?

        init(stage: FailureStage, code: FailureCode, encodedBytes: Int? = nil,
             sourceWidth: Int? = nil, sourceHeight: Int? = nil, orientation: Int? = nil) {
            self.stage = stage
            self.code = code
            self.encodedBytes = encodedBytes
            self.sourceWidth = sourceWidth
            self.sourceHeight = sourceHeight
            self.orientation = orientation
        }
    }

    enum DecodeResult {
        case success(ProfiledResult)
        case failure(Failure)
    }

    #if NG2_RASTER_HOST_TEST
    // Deterministic factory faults for public failure contracts. These fields
    // and branches are absent from the app and Runtime compilations.
    enum HostFaults {
        static var imageCreate = false
        static var normalizeRender = false
    }
    #endif

    private static func boundedMetadata(_ value: Int) -> Int? {
        return value >= Int(Int32.min) && value <= Int(Int32.max) ? value : nil
    }

    private static func metadataInteger(_ value: Any?) -> Int? {
        guard let number = value as? NSNumber,
              CFGetTypeID(number) != CFBooleanGetTypeID() else { return nil }
        let numeric = number.doubleValue
        guard numeric.isFinite, numeric.rounded(.towardZero) == numeric,
              numeric >= Double(Int32.min), numeric <= Double(Int32.max) else { return nil }
        return Int(numeric)
    }

    private static func sourceImage(_ source: CGImageSource) -> CGImage? {
        #if NG2_RASTER_HOST_TEST
        if HostFaults.imageCreate { return nil }
        #endif
        return CGImageSourceCreateImageAtIndex(source, 0, nil)
    }

    private static func bitmapContext(data: UnsafeMutableRawPointer?, width: Int,
                                      height: Int, space: CGColorSpace) -> CGContext? {
        #if NG2_RASTER_HOST_TEST
        if HostFaults.normalizeRender { return nil }
        #endif
        return CGContext(data: data, width: width, height: height, bitsPerComponent: 8,
            bytesPerRow: width * 4, space: space,
            bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue |
                CGImageAlphaInfo.premultipliedLast.rawValue)
    }

    /// EXIF orientation is applied before sizing. The bitmap is opaque sRGB
    /// RGBA8 with explicit byte order; no input-coordinate transform is inferred.
    static func normalize(_ image: CGImage, orientation: Int = 1,
                          outputWidth: Int = width, outputHeight: Int = height) -> Data? {
        return normalizeProfiled(image, orientation: orientation,
            outputWidth: outputWidth, outputHeight: outputHeight)?.rgba
    }

    static func normalizeProfiled(_ image: CGImage, orientation: Int = 1,
                                 outputWidth: Int = width, outputHeight: Int = height) -> ProfiledResult? {
        if case .success(let result) = normalizeDetailed(image, orientation: orientation,
            outputWidth: outputWidth, outputHeight: outputHeight) { return result }
        return nil
    }

    static func normalizeDetailed(_ image: CGImage, orientation: Int = 1,
                                  outputWidth: Int = width, outputHeight: Int = height) -> DecodeResult {
        return normalizeDetailed(image, orientation: orientation, outputWidth: outputWidth,
            outputHeight: outputHeight, sourceNs: 0, encodedBytes: nil,
            diagnosticWidth: boundedMetadata(image.width), diagnosticHeight: boundedMetadata(image.height),
            diagnosticOrientation: boundedMetadata(orientation))
    }

    private static func normalizeDetailed(_ image: CGImage, orientation: Int,
                                         outputWidth: Int, outputHeight: Int, sourceNs: UInt64,
                                         encodedBytes: Int?, diagnosticWidth: Int?, diagnosticHeight: Int?,
                                         diagnosticOrientation: Int?) -> DecodeResult {
        func failure(_ stage: FailureStage, _ code: FailureCode) -> DecodeResult {
            return .failure(Failure(stage: stage, code: code, encodedBytes: encodedBytes,
                sourceWidth: diagnosticWidth, sourceHeight: diagnosticHeight,
                orientation: diagnosticOrientation))
        }
        guard (1...8).contains(orientation) else { return failure(.metadata, .orientation) }
        guard image.width > 0, image.height > 0,
              image.width <= 4096, image.height <= 4096,
              image.width * image.height <= 8_000_000,
              outputWidth > 0, outputHeight > 0,
              outputWidth <= 4096, outputHeight <= 4096,
              outputWidth * outputHeight <= 8_000_000 else { return failure(.metadata, .sourceGeometry) }
        let swap = orientation >= 5
        let orientedWidth = swap ? image.height : image.width
        let orientedHeight = swap ? image.width : image.height
        guard orientedWidth * outputHeight == orientedHeight * outputWidth else { return failure(.metadata, .aspect) }
        guard let space = CGColorSpace(name: CGColorSpace.sRGB) else { return failure(.normalize, .renderFailed) }
        let drawStart = DispatchTime.now().uptimeNanoseconds
        var original = Data(count: image.width * image.height * 4)
        let decoded = original.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = bitmapContext(data: bytes.baseAddress, width: image.width,
                height: image.height, space: space) else { return false }
            context.setFillColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: image.width, height: image.height))
            context.setBlendMode(.normal)
            context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
            return true
        }
        guard decoded else { return failure(.normalize, .renderFailed) }
        let drawEnd = DispatchTime.now().uptimeNanoseconds
        // Orient source pixels before CoreGraphics resampling. Explicit maps
        // make all eight EXIF cases testable with asymmetric pixel sentinels.
        var copyPixels: UInt64 = 0
        // The black fill and source-over draw already made original opaque.
        // Orientation 1 is the identity, so Data can share its storage until a
        // mutation; the remaining path only reads it while resampling.
        var oriented = original
        if orientation != 1 {
            oriented = Data(count: orientedWidth * orientedHeight * 4)
            // NG-G2 BEGIN native orientation integer copy.
            let expectedPixels = image.width * image.height
            let byteCount = expectedPixels * 4
            let copied = original.withUnsafeBytes { source in
                oriented.withUnsafeMutableBytes { destination in
                    ng2_orient_rgba(source.bindMemory(to: UInt8.self).baseAddress, byteCount,
                        Int32(image.width), Int32(image.height), Int32(orientation),
                        destination.bindMemory(to: UInt8.self).baseAddress, byteCount)
                }
            }
            guard copied == expectedPixels else { return failure(.normalize, .orientationCopy) }
            copyPixels = UInt64(copied)
            // NG-G2 END native orientation integer copy.
        }
        let orientEnd = DispatchTime.now().uptimeNanoseconds
        func result(_ rgba: Data, scaleNs: UInt64) -> DecodeResult {
            return .success(ProfiledResult(rgba: rgba, trace: Trace(sourceWidth: image.width,
                sourceHeight: image.height, orientation: orientation, sourceNs: sourceNs,
                drawNs: drawEnd - drawStart, orientNs: orientEnd - drawEnd,
                scaleNs: scaleNs, copyPixels: copyPixels), diagnosticOrientation: diagnosticOrientation))
        }
        if orientedWidth == outputWidth && orientedHeight == outputHeight {
            return result(oriented, scaleNs: 0)
        }
        guard let provider = CGDataProvider(data: oriented as CFData),
              let orientedImage = CGImage(width: orientedWidth, height: orientedHeight,
                bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: orientedWidth * 4,
                space: space, bitmapInfo: CGBitmapInfo(rawValue:
                    CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue),
                provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else {
            return failure(.normalize, .renderFailed)
        }
        var output = Data(count: outputWidth * outputHeight * 4)
        let scaled = output.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = bitmapContext(data: bytes.baseAddress, width: outputWidth,
                height: outputHeight, space: space) else { return false }
            context.interpolationQuality = .high
            context.draw(orientedImage, in: CGRect(x: 0, y: 0, width: outputWidth, height: outputHeight))
            return true
        }
        return scaled ? result(output, scaleNs: DispatchTime.now().uptimeNanoseconds - orientEnd) :
            failure(.normalize, .renderFailed)
    }

    static func decode(_ encoded: Data) -> Data? {
        return decodeProfiled(encoded)?.rgba
    }

    static func decodeProfiled(_ encoded: Data) -> ProfiledResult? {
        if case .success(let result) = decodeDetailed(encoded) { return result }
        return nil
    }

    static func decodeDetailed(_ encoded: Data) -> DecodeResult {
        let sourceStart = DispatchTime.now().uptimeNanoseconds
        func failure(_ code: FailureCode, sourceWidth: Int? = nil,
                     sourceHeight: Int? = nil, orientation: Int? = nil) -> DecodeResult {
            return .failure(Failure(stage: .source, code: code, encodedBytes: encoded.count,
                sourceWidth: sourceWidth, sourceHeight: sourceHeight, orientation: orientation))
        }
        guard !encoded.isEmpty else { return failure(.encodedEmpty) }
        guard encoded.count <= 8 * 1024 * 1024 else { return failure(.encodedLimit) }
        guard let source = CGImageSourceCreateWithData(encoded as CFData, nil) else { return failure(.sourceOpen) }
        guard CGImageSourceGetCount(source) == 1 else { return failure(.imageCount) }
        // Read bounded source metadata before image creation so an image-create
        // failure still records available geometry. Missing EXIF stays nil in
        // diagnostics while the processing default remains orientation 1.
        let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
        let sourceWidth = metadataInteger(properties?[kCGImagePropertyPixelWidth])
        let sourceHeight = metadataInteger(properties?[kCGImagePropertyPixelHeight])
        let diagnosticOrientation = metadataInteger(properties?[kCGImagePropertyOrientation])
        let orientation = (properties?[kCGImagePropertyOrientation] as? NSNumber)?.intValue ?? 1
        guard let image = sourceImage(source) else {
            return failure(.imageCreate, sourceWidth: sourceWidth,
                sourceHeight: sourceHeight, orientation: diagnosticOrientation)
        }
        let sourceEnd = DispatchTime.now().uptimeNanoseconds
        return normalizeDetailed(image, orientation: orientation, outputWidth: width,
            outputHeight: height, sourceNs: sourceEnd - sourceStart, encodedBytes: encoded.count,
            diagnosticWidth: properties?[kCGImagePropertyPixelWidth] == nil ? boundedMetadata(image.width) : sourceWidth,
            diagnosticHeight: properties?[kCGImagePropertyPixelHeight] == nil ? boundedMetadata(image.height) : sourceHeight,
            diagnosticOrientation: diagnosticOrientation)
    }

    static func png(_ rgba: Data) -> Data? {
        guard rgba.count == stride * height,
              let space = CGColorSpace(name: CGColorSpace.sRGB),
              let provider = CGDataProvider(data: rgba as CFData),
              let image = CGImage(width: width, height: height, bitsPerComponent: 8,
                bitsPerPixel: 32, bytesPerRow: stride, space: space,
                bitmapInfo: CGBitmapInfo(rawValue: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue), provider: provider,
                decode: nil, shouldInterpolate: false, intent: .defaultIntent) else { return nil }
        let result = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(result, "public.png" as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(destination, image, nil)
        return CGImageDestinationFinalize(destination) ? result as Data : nil
    }
}
