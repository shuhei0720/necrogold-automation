#import <Foundation/Foundation.h>
NS_ASSUME_NONNULL_BEGIN
/// Direct-only asynchronous daemon capture. No timeout hides an outstanding
/// request: its completion remains owned by the Swift run until it drains.
@interface NG2CaptureBridge : NSObject
/// Main-thread bootstrap only; caches display identity before background work.
+ (BOOL)prepare;
/// All actual daemon requests, including legacy requests whose wait timed out.
@property (class, nonatomic, readonly) NSUInteger pendingRequests;
+ (void)legacyRequestBegan;
+ (void)legacyRequestEnded;
+ (void)requestJPEG:(void (^)(NSData * _Nullable data, NSString * _Nullable error))reply;
@end
NS_ASSUME_NONNULL_END
