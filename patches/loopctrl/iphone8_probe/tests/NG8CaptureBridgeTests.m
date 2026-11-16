// Real ObjC message/block/exception and concurrency boundaries; daemon fakes.
// This is a host contract fixture, not an iOS capture or gameplay success claim.
#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <dispatch/dispatch.h>
#import <stdatomic.h>
#import <math.h>
#import <stdio.h>
#import <stdlib.h>
#import "NG8CaptureHostTest.h"
#import "NG8CaptureBridge.h"

static void require(BOOL value, const char *name) {
    if (!value) { printf("FAIL %s\n", name); fflush(stdout); exit(1); }
}
static dispatch_time_t soon(void) { return dispatch_time(DISPATCH_TIME_NOW, 3 * NSEC_PER_SEC); }
static void waitFor(dispatch_semaphore_t gate, const char *name) {
    require(dispatch_semaphore_wait(gate, soon()) == 0, name);
}

typedef NS_ENUM(int, NG8FakeMode) {
    NG8Deferred, NG8Synchronous, NG8SynchronousBlockedSend,
    NG8ThrowRetained, NG8ThrowUnknown, NG8SynchronousThenThrow,
    NG8SynchronousErrorThenThrow, NG8APIUnavailable, NG8EncodingUnavailable,
    NG8RequestUnavailable, NG8ThreeArgumentRequest
};
typedef void (^NG8DaemonReply)(id, NSError *);
static NG8FakeMode mode;
static atomic_int sendCalls, encodingCalls, requestCalls, getterCalls, replyCalls, drainCalls;
static atomic_int descriptorReads;
static long long recordedScreen;
static CGRect recordedRect;
static NSString *recordedUTI;
static double recordedQuality;
static id payload;
static NSData *observedBytes;
static NSString *observedError;
static NG8DaemonReply daemonReply;
static BOOL getterThrows, getterFence, consumerFence, consumerThrows, prepareThrows;
static dispatch_semaphore_t sendEntered, sendRelease, synchronousCallbackEnded;
static dispatch_semaphore_t getterEntered, getterRelease, consumerEntered, consumerRelease;
static dispatch_semaphore_t requestReturned, callbackReturned, duplicateReturned, drainedSignal;

@implementation XCUIScreen
+ (instancetype)mainScreen {
    static XCUIScreen *value; static dispatch_once_t once;
    dispatch_once(&once, ^{ value = [XCUIScreen new]; });
    return value;
}
- (NSNumber *)displayID {
    atomic_fetch_add(&descriptorReads, 1);
    if (prepareThrows) [NSException raise:@"FakeDisplayFailure" format:@"private sentinel"];
    return @41;
}
@end

@interface XCTImageEncoding : NSObject
@property(nonatomic, strong) NSString *uniformTypeIdentifier;
@property(nonatomic) double compressionQuality;
- (instancetype)initWithDictionary:(NSDictionary *)spec;
- (instancetype)initWithUniformTypeIdentifier:(NSString *)uti compressionQuality:(double)quality;
+ (id)maximumCompression;
@end
@implementation XCTImageEncoding
- (instancetype)initWithDictionary:(NSDictionary *)spec {
    atomic_fetch_add(&encodingCalls, 1);
    if (mode == NG8EncodingUnavailable) return nil;
    if ((self = [super init])) {
        self.uniformTypeIdentifier = spec[@"uniformTypeIdentifier"];
        self.compressionQuality = [spec[@"compressionQuality"] doubleValue];
    }
    return self;
}
- (instancetype)initWithUniformTypeIdentifier:(NSString *)uti compressionQuality:(double)quality {
    atomic_fetch_add(&encodingCalls, 1);
    if (mode == NG8EncodingUnavailable) return nil;
    if ((self = [super init])) { self.uniformTypeIdentifier = uti; self.compressionQuality = quality; }
    return self;
}
+ (id)maximumCompression { return nil; }
@end

@interface XCTScreenshotRequest : NSObject
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding options:(id)options;
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding;
@end
@implementation XCTScreenshotRequest
+ (BOOL)instancesRespondToSelector:(SEL)selector {
    if (mode == NG8ThreeArgumentRequest && selector == NSSelectorFromString(@"initWithScreenID:rect:encoding:options:")) return NO;
    return [super instancesRespondToSelector:selector];
}
- (instancetype)recordScreen:(long long)screen rect:(CGRect)rect encoding:(id)encoding {
    atomic_fetch_add(&requestCalls, 1);
    recordedScreen = screen; recordedRect = rect;
    recordedUTI = [encoding valueForKey:@"uniformTypeIdentifier"];
    recordedQuality = [[encoding valueForKey:@"compressionQuality"] doubleValue];
    return mode == NG8RequestUnavailable ? nil : self;
}
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding options:(id)options {
    if ((self = [super init])) return [self recordScreen:screen rect:rect encoding:encoding];
    return nil;
}
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding {
    if ((self = [super init])) return [self recordScreen:screen rect:rect encoding:encoding];
    return nil;
}
@end

@interface NG8FakeImage : NSObject
- (id)data;
@end
@implementation NG8FakeImage
- (id)data {
    atomic_fetch_add(&getterCalls, 1);
    if (getterFence) { dispatch_semaphore_signal(getterEntered); waitFor(getterRelease, "getter_fence_released"); }
    if (getterThrows) [NSException raise:@"FakeDataFailure" format:@"private sentinel"];
    return payload;
}
@end

@interface XCTRunnerDaemonSession : NSObject
+ (instancetype)sharedSession;
- (void)requestScreenshotWithRequest:(id)request withReply:(NG8DaemonReply)reply;
@end
@implementation XCTRunnerDaemonSession
+ (BOOL)respondsToSelector:(SEL)selector {
    if (mode == NG8APIUnavailable && selector == @selector(sharedSession)) return NO;
    return [super respondsToSelector:selector];
}
+ (instancetype)sharedSession {
    static XCTRunnerDaemonSession *value; static dispatch_once_t once;
    dispatch_once(&once, ^{ value = [XCTRunnerDaemonSession new]; }); return value;
}
- (void)requestScreenshotWithRequest:(id)request withReply:(NG8DaemonReply)reply {
    atomic_fetch_add(&sendCalls, 1);
    if (mode == NG8ThrowUnknown) [NSException raise:@"FakeSendFailure" format:@"ownership unknown"];
    daemonReply = [reply copy];
    dispatch_semaphore_signal(sendEntered);
    if (mode == NG8Synchronous || mode == NG8SynchronousBlockedSend || mode == NG8SynchronousThenThrow || mode == NG8SynchronousErrorThenThrow) {
        NSError *error = mode == NG8SynchronousErrorThenThrow ? [NSError errorWithDomain:@"private sentinel" code:1 userInfo:nil] : nil;
        reply([NG8FakeImage new], error);
        dispatch_semaphore_signal(synchronousCallbackEnded);
    }
    if (mode == NG8SynchronousBlockedSend) waitFor(sendRelease, "send_fence_released");
    if (mode == NG8ThrowRetained || mode == NG8SynchronousThenThrow || mode == NG8SynchronousErrorThenThrow)
        [NSException raise:@"FakeSendFailure" format:@"private sentinel"];
}
@end

static void initialize(void) {
    sendEntered = dispatch_semaphore_create(0); sendRelease = dispatch_semaphore_create(0);
    synchronousCallbackEnded = dispatch_semaphore_create(0);
    getterEntered = dispatch_semaphore_create(0); getterRelease = dispatch_semaphore_create(0);
    consumerEntered = dispatch_semaphore_create(0); consumerRelease = dispatch_semaphore_create(0);
    requestReturned = dispatch_semaphore_create(0); callbackReturned = dispatch_semaphore_create(0);
    duplicateReturned = dispatch_semaphore_create(0); drainedSignal = dispatch_semaphore_create(0);
    const unsigned char original[] = { 0xff, 0xd8, 0xff, 0xd9 };
    // Byte transport only: coordinator's ImageIO tests must reject malformed JPEG.
    payload = [NSData dataWithBytes:original length:sizeof(original)];
}
static void beginRequest(void) {
    [NG8CaptureBridge requestJPEGWithReply:^(NSData *bytes, NSString *error) {
        atomic_fetch_add(&replyCalls, 1);
        observedBytes = bytes; observedError = error;
        if (consumerFence) { dispatch_semaphore_signal(consumerEntered); waitFor(consumerRelease, "consumer_fence_released"); }
        if (consumerThrows) [NSException raise:@"FakeConsumerFailure" format:@"private sentinel"];
    } drained:^{ atomic_fetch_add(&drainCalls, 1); dispatch_semaphore_signal(drainedSignal); }];
}
static void assertDescriptor(void) {
    require(atomic_load(&sendCalls) == 1, "capture_one_daemon_request");
    require(atomic_load(&requestCalls) == 1, "capture_one_request_descriptor");
    require(atomic_load(&descriptorReads) == 1, "capture_prepare_descriptor_once");
    require(recordedScreen == 41 && CGRectIsNull(recordedRect), "capture_display_and_full_rect");
    require([recordedUTI isEqualToString:@"public.jpeg"] && fabs(recordedQuality - 0.6) < 1e-12, "capture_original_jpeg_quality_descriptor");
}
static void assertSuccess(void) {
    require(atomic_load(&replyCalls) == 1 && observedError == nil && [observedBytes isEqualToData:payload], "original_bytes_one_reply");
    require(atomic_load(&getterCalls) == 1 && atomic_load(&drainCalls) == 1, "full_body_one_drain");
}
static void callRealReply(NSError *error) {
    require(daemonReply != nil, "daemon_block_retained"); daemonReply([NG8FakeImage new], error);
}
static void primary(void) {
    BOOL prepared = [NG8CaptureBridge prepare];
    beginRequest();
    // Required baseline Red: a compilable no-capture stub fails this behavior.
    assertDescriptor();
    require(prepared, "main_prepare_succeeds");
    require(atomic_load(&replyCalls) == 0 && atomic_load(&drainCalls) == 0, "deferred_not_reply_or_drained");
    callRealReply(nil); assertSuccess();
    callRealReply(nil);
    require(atomic_load(&getterCalls) == 1 && atomic_load(&replyCalls) == 1 && atomic_load(&drainCalls) == 1, "duplicate_no_getter_reply_or_drain");
}
static void simpleFailure(NSString *name) {
    NSString *expected = @"bytes_invalid";
    if ([name isEqualToString:@"empty"]) payload = [NSData data];
    else if ([name isEqualToString:@"nil_data"]) payload = nil;
    else if ([name isEqualToString:@"oversize"]) payload = [NSMutableData dataWithLength:8 * 1024 * 1024 + 1];
    else if ([name isEqualToString:@"wrong_type"]) payload = @"private sentinel";
    else if ([name isEqualToString:@"getter_exception"]) { getterThrows = YES; expected = @"reply_exception"; }
    else if ([name isEqualToString:@"daemon_error"]) expected = @"capture_failed";
    require([NG8CaptureBridge prepare], "failure_prepare"); beginRequest(); assertDescriptor();
    NSError *error = [name isEqualToString:@"daemon_error"] ? [NSError errorWithDomain:@"private sentinel" code:2 userInfo:nil] : nil;
    callRealReply(error);
    require(atomic_load(&replyCalls) == 1 && observedBytes == nil && [observedError isEqualToString:expected], "fixed_failure_no_raw_exception");
    require(atomic_load(&drainCalls) == 1, "failure_full_body_drained");
    callRealReply(nil);
    require(atomic_load(&replyCalls) == 1 && [observedError isEqualToString:expected] && atomic_load(&drainCalls) == 1, "first_failure_immutable_after_late_duplicate");
}
static void retainedThrow(BOOL unknown) {
    mode = unknown ? NG8ThrowUnknown : NG8ThrowRetained;
    require([NG8CaptureBridge prepare], "throw_prepare"); beginRequest();
    require(atomic_load(&sendCalls) == 1 && atomic_load(&replyCalls) == 1 && observedBytes == nil && [observedError isEqualToString:@"request_exception"], "send_throw_one_fixed_failure");
    require(atomic_load(&drainCalls) == 0, "synthetic_error_is_not_daemon_drain");
    if (unknown) return;
    callRealReply(nil);
    require(atomic_load(&replyCalls) == 1 && [observedError isEqualToString:@"request_exception"] && observedBytes == nil, "late_success_does_not_replace_send_failure");
    require(atomic_load(&drainCalls) == 1 && atomic_load(&getterCalls) == 0, "late_callback_drain_only");
    callRealReply(nil);
    require(atomic_load(&drainCalls) == 1 && atomic_load(&replyCalls) == 1, "late_duplicate_drains_once");
}
static void synchronousHeld(void) {
    mode = NG8SynchronousBlockedSend;
    require([NG8CaptureBridge prepare], "sync_prepare");
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ @autoreleasepool { beginRequest(); dispatch_semaphore_signal(requestReturned); } });
    waitFor(synchronousCallbackEnded, "sync_callback_finished_while_send_held");
    require(atomic_load(&getterCalls) == 1 && atomic_load(&replyCalls) == 0 && atomic_load(&drainCalls) == 0, "sync_callback_does_not_release_send_ownership");
    dispatch_semaphore_signal(sendRelease); waitFor(requestReturned, "sync_send_really_returned"); assertSuccess();
}
static void callbackFence(BOOL consumer) {
    getterFence = !consumer; consumerFence = consumer;
    require([NG8CaptureBridge prepare], "callback_fence_prepare"); beginRequest(); assertDescriptor();
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ @autoreleasepool { callRealReply(nil); dispatch_semaphore_signal(callbackReturned); } });
    waitFor(consumer ? consumerEntered : getterEntered, "callback_body_fence_entered");
    require(atomic_load(&drainCalls) == 0, "callback_body_still_owns_drain");
    if (!consumer) {
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ @autoreleasepool { callRealReply(nil); dispatch_semaphore_signal(duplicateReturned); } });
        waitFor(duplicateReturned, "duplicate_during_getter_returns");
        require(atomic_load(&getterCalls) == 1 && atomic_load(&replyCalls) == 0 && atomic_load(&drainCalls) == 0, "duplicate_during_getter_no_early_work_or_drain");
    }
    dispatch_semaphore_signal(consumer ? consumerRelease : getterRelease);
    waitFor(callbackReturned, "real_callback_body_returned"); assertSuccess();
}
static void synchronousThrow(BOOL errorFirst) {
    mode = errorFirst ? NG8SynchronousErrorThenThrow : NG8SynchronousThenThrow;
    require([NG8CaptureBridge prepare], "sync_throw_prepare"); beginRequest();
    require(atomic_load(&sendCalls) == 1 && atomic_load(&replyCalls) == 1 && observedBytes == nil, "sync_throw_one_failure");
    require([observedError isEqualToString:errorFirst ? @"capture_failed" : @"request_exception"], "sync_throw_preserves_first_failure");
    require(atomic_load(&drainCalls) == 1, "sync_callback_and_send_unwind_drained");
    callRealReply(nil); require(atomic_load(&drainCalls) == 1 && atomic_load(&replyCalls) == 1, "sync_throw_late_duplicate_ignored");
}
static void unavailable(NSString *name) {
    mode = [name isEqualToString:@"api_unavailable"] ? NG8APIUnavailable : [name isEqualToString:@"encoding_unavailable"] ? NG8EncodingUnavailable : NG8RequestUnavailable;
    require([NG8CaptureBridge prepare], "unavailable_prepare"); beginRequest();
    require(atomic_load(&sendCalls) == 0 && atomic_load(&replyCalls) == 1 && observedBytes == nil, "pre_send_failure_no_daemon");
    NSString *expected = mode == NG8RequestUnavailable ? @"request_unavailable" : @"api_unavailable";
    require([observedError isEqualToString:expected] && atomic_load(&drainCalls) == 1, "proven_no_send_can_drain");
}
static void offMainPrepare(void) {
    __block BOOL prepared = YES;
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{ @autoreleasepool { prepared = [NG8CaptureBridge prepare]; dispatch_semaphore_signal(requestReturned); } });
    waitFor(requestReturned, "off_main_prepare_returned");
    require(!prepared && atomic_load(&descriptorReads) == 0 && atomic_load(&sendCalls) == 0, "off_main_prepare_no_descriptor_or_capture");
}
int main(int argc, const char **argv) { @autoreleasepool {
    initialize();
    NSString *name = argc > 1 ? [NSString stringWithUTF8String:argv[1]] : @"primary";
    if ([name isEqualToString:@"primary"]) primary();
    else if ([@[@"empty", @"nil_data", @"oversize", @"wrong_type", @"getter_exception", @"daemon_error"] containsObject:name]) simpleFailure(name);
    else if ([name isEqualToString:@"throw_retained"]) retainedThrow(NO);
    else if ([name isEqualToString:@"throw_unknown"]) retainedThrow(YES);
    else if ([name isEqualToString:@"sync_send_held"]) synchronousHeld();
    else if ([name isEqualToString:@"getter_fence"]) callbackFence(NO);
    else if ([name isEqualToString:@"consumer_fence"]) callbackFence(YES);
    else if ([name isEqualToString:@"sync_then_throw"]) synchronousThrow(NO);
    else if ([name isEqualToString:@"sync_error_then_throw"]) synchronousThrow(YES);
    else if ([@[@"api_unavailable", @"encoding_unavailable", @"request_unavailable"] containsObject:name]) unavailable(name);
    else if ([name isEqualToString:@"off_main_prepare"]) offMainPrepare();
    else if ([name isEqualToString:@"prepare_exception"]) {
        prepareThrows = YES;
        require(![NG8CaptureBridge prepare] && atomic_load(&descriptorReads) == 1 && atomic_load(&sendCalls) == 0, "prepare_exception_no_capture");
    } else if ([name isEqualToString:@"never_callback"]) {
        require([NG8CaptureBridge prepare], "never_prepare"); beginRequest(); assertDescriptor();
        require(atomic_load(&replyCalls) == 0 && atomic_load(&drainCalls) == 0, "never_callback_keeps_unresolved_ownership");
    } else if ([name isEqualToString:@"three_arg_request"]) { mode = NG8ThreeArgumentRequest; primary(); }
    else if ([name isEqualToString:@"exact_maximum"]) { payload = [NSMutableData dataWithLength:8 * 1024 * 1024]; primary(); }
    else if ([name isEqualToString:@"consumer_exception"]) {
        consumerThrows = YES;
        require([NG8CaptureBridge prepare], "consumer_exception_prepare"); beginRequest(); callRealReply(nil);
        require(atomic_load(&replyCalls) == 1 && atomic_load(&drainCalls) == 1, "consumer_exception_no_second_reply_and_finally_drain");
    } else require(NO, "known_fixture_case");
    printf("PASS NG8 bridge %s (real ObjC boundary, daemon fake)\n", name.UTF8String);
    return 0;
} }
