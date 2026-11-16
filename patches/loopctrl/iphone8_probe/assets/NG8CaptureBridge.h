#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Original JPEG transport for the isolated iPhone 8 capture-only build.
/// This class has no relationship to NG2CaptureBridge's display/pending state.
@interface NG8CaptureBridge : NSObject

/// Main-thread descriptor read only. No AX, app activation, or image capture.
+ (BOOL)prepare;

/// At most one reply containing original, nonempty NSData up to 8 MiB, or a
/// fixed error code. No image decode, raster conversion, or fallback encoder.
///
/// drained fires at most once, after the private send has returned/unwound AND
/// the first real daemon callback's entire body and reply consumer have ended.
/// A send exception is a failure reply, not proof of daemon drain. Without a
/// real callback after an ambiguous send, drained must remain uncalled.
/// The method's own return and the reply callback are not drain evidence.
+ (void)requestJPEGWithReply:(void (^)(NSData * _Nullable data,
                                      NSString * _Nullable errorCode))reply
                    drained:(void (^)(void))drained;
@end

NS_ASSUME_NONNULL_END
