// Modified for NecroGold NG-G2; direct request adapted from LoopCtrl's
// ObjCException.m (Apache-2.0). No public screenshot/main-thread fallback.
#import "NG2CaptureBridge.h"
#import "ObjCException.h"
#import <CoreGraphics/CoreGraphics.h>
#ifndef NG2_CAPTURE_HOST_TEST
#import <XCTest/XCTest.h>
#else
#import "NG2CaptureHostTest.h"
#endif
#import <objc/message.h>
#import <stdatomic.h>
#pragma clang diagnostic ignored "-Warc-performSelector-leaks"
@implementation NG2CaptureBridge
static long long ng2ScreenID = 0;
static atomic_uint ng2Pending = 0;
+ (NSUInteger)pendingRequests { return atomic_load(&ng2Pending); }
+ (void)legacyRequestBegan { atomic_fetch_add(&ng2Pending, 1); }
+ (void)legacyRequestEnded { atomic_fetch_sub(&ng2Pending, 1); }
+ (BOOL)prepare {
    if (![NSThread isMainThread]) { return NO; }
    @try {
        long long value = [[XCUIScreen.mainScreen valueForKey:@"displayID"] longLongValue];
        if (value <= 0) { return NO; }
        ng2ScreenID = value;
        return YES;
    } @catch (__unused NSException *exception) { return NO; }
}
+ (void)requestJPEG:(void (^)(NSData *, NSString *))reply {
    @try {
        Class encodingClass = NSClassFromString(@"XCTImageEncoding");
        Class sessionClass = NSClassFromString(@"XCTRunnerDaemonSession");
        Class requestClass = NSClassFromString(@"XCTScreenshotRequest");
        SEL shared = NSSelectorFromString(@"sharedSession");
        SEL request = NSSelectorFromString(@"requestScreenshotWithRequest:withReply:");
        if (!encodingClass || !sessionClass || !requestClass ||
            ![sessionClass respondsToSelector:shared]) { reply(nil, @"direct capture API unavailable"); return; }
        NSString *why = nil;
        id encoding = [ObjCException makeImageEncoding:encodingClass uti:@"public.jpeg" quality:0.6 diagnosis:&why];
        id session = [sessionClass performSelector:shared];
        if (!encoding || ![session respondsToSelector:request]) { reply(nil, @"direct capture session unavailable"); return; }
        if (ng2ScreenID <= 0) { reply(nil,@"direct capture display unprepared"); return; }
        long long screenID = ng2ScreenID;
        id req = nil;
        SEL init4 = NSSelectorFromString(@"initWithScreenID:rect:encoding:options:");
        SEL init3 = NSSelectorFromString(@"initWithScreenID:rect:encoding:");
        if ([requestClass instancesRespondToSelector:init4]) {
            id (*fn)(id,SEL,long long,CGRect,id,id) = (void *)objc_msgSend;
            req = fn([requestClass alloc],init4,screenID,CGRectNull,encoding,nil);
        } else if ([requestClass instancesRespondToSelector:init3]) {
            id (*fn)(id,SEL,long long,CGRect,id) = (void *)objc_msgSend;
            req = fn([requestClass alloc],init3,screenID,CGRectNull,encoding);
        }
        if (!req) { reply(nil, @"direct capture request unavailable"); return; }
        void (*send)(id,SEL,id,id) = (void *)objc_msgSend;
        NSLock *completionLock = [NSLock new];
        __block BOOL completed = NO;
        [self legacyRequestBegan];
        send(session,request,req,^(id image,NSError *error) {
            [completionLock lock];
            BOOL first = !completed; completed = YES;
            [completionLock unlock];
            if (!first) { return; }
            [self legacyRequestEnded];
            @try {
                if (error || ![image respondsToSelector:@selector(data)]) {
                    reply(nil,@"direct capture failed"); return;
                }
                NSData *data = [image performSelector:@selector(data)];
                if (![data isKindOfClass:[NSData class]] || data.length == 0 || data.length > 8*1024*1024) {
                    reply(nil,@"direct capture bytes invalid"); return;
                }
                reply(data,nil);
            } @catch (__unused NSException *exception) { reply(nil,@"direct capture reply exception"); }
        });
    } @catch (__unused NSException *exception) { reply(nil,@"direct capture request exception"); }
}
@end
