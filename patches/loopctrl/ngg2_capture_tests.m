#import "NG2CaptureHostTest.h"
#import "NG2CaptureBridge.h"
#import "ObjCException.h"

@implementation XCUIScreen
+ (instancetype)mainScreen { static XCUIScreen *screen; if(!screen)screen=[XCUIScreen new]; return screen; }
- (NSNumber *)displayID { return @1; }
@end
@interface XCTImageEncoding : NSObject
@property(nonatomic,strong) NSString *uniformTypeIdentifier;
- (instancetype)initWithDictionary:(NSDictionary *)spec;
@end
@implementation XCTImageEncoding
- (instancetype)initWithDictionary:(NSDictionary *)spec {
    if((self=[super init]))_uniformTypeIdentifier=spec[@"uniformTypeIdentifier"]; return self;
}
@end
@interface XCTScreenshotRequest : NSObject
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding options:(id)options;
@end
@implementation XCTScreenshotRequest
- (instancetype)initWithScreenID:(long long)screen rect:(CGRect)rect encoding:(id)encoding options:(id)options { return [super init]; }
@end
@interface NG2FakeImage : NSObject
- (NSData *)data;
@end
@implementation NG2FakeImage
- (NSData *)data { return [@"fake daemon encoded image" dataUsingEncoding:NSUTF8StringEncoding]; }
@end
@interface XCTRunnerDaemonSession : NSObject
@property(nonatomic,copy) void (^reply)(id,NSError *);
+ (instancetype)sharedSession;
- (void)requestScreenshotWithRequest:(id)request withReply:(void (^)(id,NSError *))reply;
@end
@implementation XCTRunnerDaemonSession
+ (instancetype)sharedSession { static XCTRunnerDaemonSession *session; if(!session)session=[self new]; return session; }
- (void)requestScreenshotWithRequest:(id)request withReply:(void (^)(id,NSError *))reply { self.reply=reply; }
@end
static void require(BOOL value,const char *name) { if(!value){printf("FAIL %s\n",name);exit(1);} }
int main(void) { @autoreleasepool {
    require([NG2CaptureBridge prepare],"main_display_prepared");
    id encoding=[[XCTImageEncoding alloc]initWithDictionary:@{@"uniformTypeIdentifier":@"public.jpeg"}];
    NSString *why=nil;
    NSData *legacy=[ObjCException daemonScreenshotWithEncoding:encoding timeout:0.01 why:&why];
    require(legacy==nil&&[NG2CaptureBridge pendingRequests]==1,"legacy_timeout_keeps_actual_pending");
    void (^oldReply)(id,NSError *)=[XCTRunnerDaemonSession sharedSession].reply;
    oldReply([NG2FakeImage new],nil);
    require([NG2CaptureBridge pendingRequests]==0,"legacy_actual_reply_releases_pending");
    oldReply([NG2FakeImage new],nil);
    require([NG2CaptureBridge pendingRequests]==0,"duplicate_legacy_reply_no_underflow");
    __block int callbacks=0;
    [NG2CaptureBridge requestJPEG:^(NSData *bytes,NSString *error){ require(bytes.length>0&&!error,"native_reply_bytes");++callbacks; }];
    require([NG2CaptureBridge pendingRequests]==1&&callbacks==0,"native_actual_request_pending");
    void (^nativeReply)(id,NSError *)=[XCTRunnerDaemonSession sharedSession].reply;
    nativeReply([NG2FakeImage new],nil);
    require([NG2CaptureBridge pendingRequests]==0&&callbacks==1,"native_actual_reply_releases_pending");
    nativeReply([NG2FakeImage new],nil);
    require([NG2CaptureBridge pendingRequests]==0&&callbacks==1,"duplicate_native_reply_no_underflow");
    printf("PASS production legacy timeout and native daemon callback exclusion; daemon classes faked\n");
    return 0;
} }
