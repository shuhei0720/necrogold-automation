// iPhone 8 capture-only transport. Derived from LoopCtrl's NG2CaptureBridge and
// ObjCException.m (Apache-2.0); the original production sources remain unchanged.
#import "NG8CaptureBridge.h"
#import <CoreGraphics/CoreGraphics.h>
#import <objc/message.h>
#import <objc/runtime.h>
#import <stdatomic.h>
#import <string.h>
#ifndef NG8_CAPTURE_HOST_TEST
#import <XCTest/XCTest.h>
#else
#import "NG8CaptureHostTest.h"
#endif
#pragma clang diagnostic ignored "-Warc-performSelector-leaks"

// One request owns its private send, its first real daemon callback's data work,
// and the consumer separately. No synthetic reply can stand in for a daemon
// callback. Completion is the final owned-work handoff, never proof of the
// daemon block's literal stack return or framework-internal cleanup.
@interface NG8CaptureTicket : NSObject
- (instancetype)initWithReply:(void (^)(NSData *, NSString *))reply drained:(void (^)(void))drained;
- (void)beforeSend;
- (void)sendReturnedWithException:(BOOL)exception;
- (void)failBeforeSend:(NSString *)code;
- (BOOL)claimCallbackReadingData:(BOOL *)read;
- (void)fail:(NSString *)code;
- (void)candidate:(NSData *)bytes;
- (void)callbackBodyEnded;
@end

@implementation NG8CaptureTicket {
    NSLock *_lock;
    void (^_reply)(NSData *, NSString *);
    void (^_drained)(void);
    NSData *_bytes;
    NSString *_failure;
    BOOL _sendEntered, _sendEnded, _noSend;
    BOOL _callbackClaimed, _callbackEnded;
    BOOL _replyClaimed, _replyEnded, _drainClaimed;
}
- (instancetype)initWithReply:(void (^)(NSData *, NSString *))reply drained:(void (^)(void))drained {
    if ((self = [super init])) {
        _lock = [NSLock new]; _reply = [reply copy]; _drained = [drained copy];
    }
    return self;
}
- (void)beforeSend { [_lock lock]; _sendEntered = YES; [_lock unlock]; }
- (void)fail:(NSString *)code {
    [_lock lock];
    if (!_failure && !_replyClaimed) { _failure = code; _bytes = nil; }
    [_lock unlock];
}
- (void)candidate:(NSData *)bytes {
    // Copy before releasing callback ownership: a mutable daemon buffer must
    // not change the original artifact after its reply has been delivered.
    NSData *fixed = [bytes copy];
    [_lock lock]; if (!_failure && !_replyClaimed) _bytes = fixed; [_lock unlock];
}
- (BOOL)claimCallbackReadingData:(BOOL *)read {
    [_lock lock];
    BOOL first = !_callbackClaimed;
    if (first) _callbackClaimed = YES;
    *read = first && !_failure;
    [_lock unlock]; return first;
}
- (void)advance {
    void (^reply)(NSData *, NSString *) = nil;
    void (^drained)(void) = nil;
    NSData *bytes = nil; NSString *failure = nil;
    [_lock lock];
    // A synchronous success is only a candidate until send returns. If send
    // subsequently throws, request_exception wins over that candidate. An
    // earlier callback/getter failure remains the first immutable failure.
    if (!_replyClaimed && (_failure || (_sendEnded && _callbackEnded && _bytes))) {
        _replyClaimed = YES;
        reply = _reply; _reply = nil;
        failure = _failure; bytes = failure ? nil : _bytes; _bytes = nil;
    } else if (!_drainClaimed && _sendEnded && (_noSend || _callbackEnded) && _replyEnded) {
        _drainClaimed = YES; drained = _drained; _drained = nil;
    }
    [_lock unlock];
    if (reply) {
        @try { reply(bytes, failure); }
        @catch (__unused NSException *exception) {
            // The consumer has already been invoked; calling it again with an
            // error would violate at-most-once delivery and can throw again.
        } @finally {
            [_lock lock]; _replyEnded = YES; [_lock unlock];
            [self advance];
        }
    } else if (drained) {
        // Final handoff only. There is no ticket mutation or data/consumer work
        // after this notification. Its receiver may only enqueue an event.
        @try { drained(); } @catch (__unused NSException *exception) {}
    }
}
- (void)sendReturnedWithException:(BOOL)exception {
    [_lock lock];
    if (exception && !_failure && !_replyClaimed) { _failure = @"request_exception"; _bytes = nil; }
    _sendEnded = YES;
    [_lock unlock]; [self advance];
}
- (void)failBeforeSend:(NSString *)code {
    [_lock lock];
    // This entry is only valid before the private send was entered. An
    // ambiguous send exception must use sendReturnedWithException instead.
    if (!_sendEntered) {
        _noSend = YES; _sendEnded = YES;
        if (!_failure && !_replyClaimed) _failure = code;
    }
    [_lock unlock]; [self advance];
}
- (void)callbackBodyEnded {
    [_lock lock]; _callbackEnded = YES; [_lock unlock];
    [self advance];
}
@end

// Preserve the production encoding-constructor order and its API probes.
// Like the baseline, maximumCompression is a factory fallback with a fixed
// system quality; 0.6 is the requested quality, not a JPEG-inferred measurement.
static id NG8MakeImageEncoding(Class encodingClass) {
    SEL dictionary = NSSelectorFromString(@"initWithDictionary:");
    if ([encodingClass instancesRespondToSelector:dictionary]) {
        id value = [[encodingClass alloc] performSelector:dictionary withObject:@{
            @"uniformTypeIdentifier": @"public.jpeg", @"compressionQuality": @0.6 }];
        BOOL took = NO;
        @try { took = [value valueForKey:@"uniformTypeIdentifier"] != nil; }
        @catch (__unused NSException *exception) {}
        if (value && took) return value;
    }
    SEL maximum = NSSelectorFromString(@"maximumCompression");
    if ([encodingClass respondsToSelector:maximum]) {
        id value = [encodingClass performSelector:maximum];
        if (value && !class_isMetaClass(object_getClass(value))) return value;
    }
    SEL designated = NSSelectorFromString(@"initWithUniformTypeIdentifier:compressionQuality:");
    if ([encodingClass instancesRespondToSelector:designated]) {
        NSMethodSignature *signature = [encodingClass instanceMethodSignatureForSelector:designated];
        const char *qualityType = signature.numberOfArguments >= 4 ? [signature getArgumentTypeAtIndex:3] : NULL;
        BOOL floatQuality = qualityType && strcmp(qualityType, @encode(float)) == 0;
        BOOL doubleQuality = qualityType && strcmp(qualityType, @encode(double)) == 0;
        // An unsupported signature cannot be initialized safely. Do not create
        // a +1 allocated object that no initializer can consume in that case.
        if (!floatQuality && !doubleQuality) return nil;
        void *(*allocate)(Class, SEL) = (void *)objc_msgSend;
        void *allocated = allocate(encodingClass, @selector(alloc));
        void *created = NULL;
        if (allocated && floatQuality) {
            void *(*initialize)(void *, SEL, void *, float) = (void *)objc_msgSend;
            created = initialize(allocated, designated, (__bridge void *)@"public.jpeg", (float)0.6);
        } else if (allocated && doubleQuality) {
            void *(*initialize)(void *, SEL, void *, double) = (void *)objc_msgSend;
            created = initialize(allocated, designated, (__bridge void *)@"public.jpeg", 0.6);
        }
        if (created) return (__bridge_transfer id)created;
    }
    return nil;
}

@implementation NG8CaptureBridge
static atomic_llong ng8ScreenID = 0;
+ (BOOL)prepare {
    if (![NSThread isMainThread]) return NO;
    @try {
        long long value = [[XCUIScreen.mainScreen valueForKey:@"displayID"] longLongValue];
        if (value <= 0) { atomic_store(&ng8ScreenID, 0); return NO; }
        atomic_store(&ng8ScreenID, value); return YES;
    } @catch (__unused NSException *exception) { atomic_store(&ng8ScreenID, 0); return NO; }
}
+ (void)requestJPEGWithReply:(void (^)(NSData *, NSString *))reply
                    drained:(void (^)(void))drained {
    NG8CaptureTicket *ticket = [[NG8CaptureTicket alloc] initWithReply:reply drained:drained];
    __block BOOL sendEntered = NO;
    @try {
        Class encodingClass = NSClassFromString(@"XCTImageEncoding");
        Class sessionClass = NSClassFromString(@"XCTRunnerDaemonSession");
        Class requestClass = NSClassFromString(@"XCTScreenshotRequest");
        SEL shared = NSSelectorFromString(@"sharedSession");
        SEL request = NSSelectorFromString(@"requestScreenshotWithRequest:withReply:");
        if (!encodingClass || !sessionClass || !requestClass || ![sessionClass respondsToSelector:shared]) {
            [ticket failBeforeSend:@"api_unavailable"]; return;
        }
        id encoding = NG8MakeImageEncoding(encodingClass);
        id session = [sessionClass performSelector:shared];
        if (!encoding || ![session respondsToSelector:request]) {
            [ticket failBeforeSend:@"api_unavailable"]; return;
        }
        long long screen = atomic_load(&ng8ScreenID);
        if (screen <= 0) { [ticket failBeforeSend:@"prepare_unavailable"]; return; }
        id descriptor = nil;
        SEL four = NSSelectorFromString(@"initWithScreenID:rect:encoding:options:");
        SEL three = NSSelectorFromString(@"initWithScreenID:rect:encoding:");
        if ([requestClass instancesRespondToSelector:four]) {
            id (*initialize)(id, SEL, long long, CGRect, id, id) = (void *)objc_msgSend;
            descriptor = initialize([requestClass alloc], four, screen, CGRectNull, encoding, nil);
        } else if ([requestClass instancesRespondToSelector:three]) {
            id (*initialize)(id, SEL, long long, CGRect, id) = (void *)objc_msgSend;
            descriptor = initialize([requestClass alloc], three, screen, CGRectNull, encoding);
        }
        if (!descriptor) { [ticket failBeforeSend:@"request_unavailable"]; return; }
        void (*send)(id, SEL, id, id) = (void *)objc_msgSend;
        [ticket beforeSend]; sendEntered = YES;
        send(session, request, descriptor, ^(id image, NSError *error) {
            BOOL read = NO;
            if (![ticket claimCallbackReadingData:&read]) return;
            @try {
                if (!read) return;
                if (error || ![image respondsToSelector:@selector(data)]) {
                    [ticket fail:@"capture_failed"]; return;
                }
                NSData *data = [image performSelector:@selector(data)];
                if (![data isKindOfClass:[NSData class]] || data.length == 0 || data.length > 8 * 1024 * 1024) {
                    [ticket fail:@"bytes_invalid"]; return;
                }
                [ticket candidate:data];
            } @catch (__unused NSException *exception) {
                [ticket fail:@"reply_exception"];
            } @finally {
                // All getter/copy/exception work is finished before this
                // handoff; advance also waits for the consumer's real return.
                [ticket callbackBodyEnded];
            }
        });
        [ticket sendReturnedWithException:NO];
    } @catch (__unused NSException *exception) {
        if (sendEntered) [ticket sendReturnedWithException:YES];
        else [ticket failBeforeSend:@"request_exception"];
    }
}
@end
