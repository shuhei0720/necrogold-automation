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
/// drained is a final owned-work handoff, at most once: the private send has
/// returned/unwound, and all first-callback data/getter/copy work and the primary
/// reply consumer have ended. No data/getter/consumer or ticket-state mutation
/// follows that handoff. It does NOT prove the daemon block's literal stack
/// return or daemon-internal cleanup; callback_return_verified remains false.
/// This boundary belongs only to the isolated capture-only capability and does
/// not change the production native capture/drain contract.
///
/// The drained receiver must only enqueue a nonblocking completion event. It
/// must not acquire locks, wait, query AX, parse metadata, or hash bytes. The
/// receiving coordinator tracks its own queued work separately.
/// A send exception is a failure reply, not a completed daemon callback. Without
/// a real callback after an ambiguous send, drained must remain uncalled.
/// The method's own return and the primary reply are not completion evidence.
+ (void)requestJPEGWithReply:(void (^)(NSData * _Nullable data,
                                      NSString * _Nullable errorCode))reply
                    drained:(void (^)(void))drained;
@end

NS_ASSUME_NONNULL_END
