import Foundation
import CoreGraphics
import ImageIO

enum NG2Raster {
    static let width = 896
    static let height = 414
    static let stride = width * 4

    /// EXIF orientation is applied before sizing. The bitmap is opaque sRGB
    /// RGBA8 with explicit byte order; no input-coordinate transform is inferred.
    static func normalize(_ image: CGImage, orientation: Int = 1,
                          outputWidth: Int = width, outputHeight: Int = height) -> Data? {
        guard (1...8).contains(orientation), image.width > 0, image.height > 0,
              image.width <= 4096, image.height <= 4096,
              image.width * image.height <= 8_000_000,
              outputWidth > 0, outputHeight > 0,
              outputWidth <= 4096, outputHeight <= 4096,
              outputWidth * outputHeight <= 8_000_000,
              let space = CGColorSpace(name: CGColorSpace.sRGB) else { return nil }
        let swap = orientation >= 5
        let orientedWidth = swap ? image.height : image.width
        let orientedHeight = swap ? image.width : image.height
        guard orientedWidth * outputHeight == orientedHeight * outputWidth else { return nil }
        var original = Data(count: image.width * image.height * 4)
        let decoded = original.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = CGContext(data: bytes.baseAddress, width: image.width,
                height: image.height, bitsPerComponent: 8, bytesPerRow: image.width * 4,
                space: space, bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            context.setFillColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: image.width, height: image.height))
            context.setBlendMode(.normal)
            context.draw(image, in: CGRect(x: 0, y: 0, width: image.width, height: image.height))
            return true
        }
        guard decoded else { return nil }
        // Orient source pixels before CoreGraphics resampling. Explicit maps
        // make all eight EXIF cases testable with asymmetric pixel sentinels.
        var oriented = Data(count: orientedWidth * orientedHeight * 4)
        original.withUnsafeBytes { source in
            oriented.withUnsafeMutableBytes { destination in
                let src = source.bindMemory(to: UInt8.self)
                let dst = destination.bindMemory(to: UInt8.self)
                for y in 0..<orientedHeight {
                    for x in 0..<orientedWidth {
                        let p: (Int, Int)
                        switch orientation {
                        case 2: p = (image.width-1-x, y)
                        case 3: p = (image.width-1-x, image.height-1-y)
                        case 4: p = (x, image.height-1-y)
                        case 5: p = (y, x)
                        case 6: p = (y, image.height-1-x)
                        case 7: p = (image.width-1-y, image.height-1-x)
                        case 8: p = (image.width-1-y, x)
                        default: p = (x, y)
                        }
                        let a = (p.1 * image.width + p.0) * 4
                        let b = (y * orientedWidth + x) * 4
                        dst[b] = src[a]; dst[b+1] = src[a+1]; dst[b+2] = src[a+2]; dst[b+3] = 255
                    }
                }
            }
        }
        if orientedWidth == outputWidth && orientedHeight == outputHeight { return oriented }
        guard let provider = CGDataProvider(data: oriented as CFData),
              let orientedImage = CGImage(width: orientedWidth, height: orientedHeight,
                bitsPerComponent: 8, bitsPerPixel: 32, bytesPerRow: orientedWidth * 4,
                space: space, bitmapInfo: CGBitmapInfo(rawValue:
                    CGBitmapInfo.byteOrder32Big.rawValue | CGImageAlphaInfo.premultipliedLast.rawValue),
                provider: provider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else { return nil }
        var output = Data(count: outputWidth * outputHeight * 4)
        let scaled = output.withUnsafeMutableBytes { bytes -> Bool in
            guard let context = CGContext(data: bytes.baseAddress, width: outputWidth,
                height: outputHeight, bitsPerComponent: 8, bytesPerRow: outputWidth * 4,
                space: space, bitmapInfo: CGBitmapInfo.byteOrder32Big.rawValue |
                    CGImageAlphaInfo.premultipliedLast.rawValue) else { return false }
            context.interpolationQuality = .high
            context.draw(orientedImage, in: CGRect(x: 0, y: 0, width: outputWidth, height: outputHeight))
            return true
        }
        return scaled ? output : nil
    }

    static func decode(_ encoded: Data) -> Data? {
        guard !encoded.isEmpty, encoded.count <= 8 * 1024 * 1024,
              let source = CGImageSourceCreateWithData(encoded as CFData, nil),
              CGImageSourceGetCount(source) == 1,
              let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { return nil }
        let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any]
        let orientation = (properties?[kCGImagePropertyOrientation] as? NSNumber)?.intValue ?? 1
        return normalize(image, orientation: orientation)
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
