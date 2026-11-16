// iPhone 8 capture-only transport: assertion-Red stub, not deployable.
// Green must not be implemented until the real macOS ObjC fixture observes Red.
#import "NG8CaptureBridge.h"

@implementation NG8CaptureBridge
+ (BOOL)prepare { return NO; }
+ (void)requestJPEGWithReply:(void (^)(NSData *, NSString *))reply
                    drained:(void (^)(void))drained {
    // No private API was called, so this stub owns no daemon request.
    reply(nil, @"not_implemented");
    drained();
}
@end
