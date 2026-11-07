#import <Foundation/Foundation.h>
#import <CoreGraphics/CoreGraphics.h>
@interface XCUIScreen : NSObject
@property(class,nonatomic,readonly) XCUIScreen *mainScreen;
@property(nonatomic,readonly) NSNumber *displayID;
@end
