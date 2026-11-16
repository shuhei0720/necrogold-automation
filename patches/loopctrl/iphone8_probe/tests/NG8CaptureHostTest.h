#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>

/// The real bridge imports XCTest on-device. Only the host fixture defines this
/// public descriptor shape; private daemon classes are found through runtime APIs.
@interface XCUIScreen : NSObject
@property(class, nonatomic, readonly) XCUIScreen *mainScreen;
@property(nonatomic, readonly) NSNumber *displayID;
@end
