import Foundation
import CoreGraphics
func check(_ value: @autoclosure () -> Bool, _ label: String) { if !value() { fatalError(label) } }
@main
struct DeviceGeometryBindingFixture {
    static func main() {
        let old = NG2DeviceGeometryBinding.local()
        check(old.legacyPassthrough, "legacy_default_unchanged")
        var command = NG2Command()
        command.kind = 99; command.direction = 88; command.x = -123; command.y = Int32.max
        let oldPoint = old.resolvedPoint(command)
        check(oldPoint.map { Double($0.x) == -123 && Double($0.y) == Double(Int32.max) } == true, "legacy_extra_command_passthrough")
        let p8 = "iPhone10,1".withCString { ng2_device_geometry_profile($0,375,667)! }
        let spare = NG2DeviceGeometryBinding(profile: p8, panelWidth:375, panelHeight:667, model:"iPhone10,1")
        command.kind=4; command.direction=1; command.x=207; command.y=49
        check(spare.resolvedPoint(command) == nil, "gap31_closed_before_begin")
        var qualifiedFixture = p8.pointee
        qualifiedFixture.qualification_gaps = 0
        withUnsafePointer(to: &qualifiedFixture) { pointer in
            let fixture = NG2DeviceGeometryBinding(profile:pointer, panelWidth:375, panelHeight:667, model:"iPhone10,1")
            let mapped=fixture.resolvedPoint(command)
            check(mapped?.x == 187.5 && mapped?.y == 40, "Double_halfpoint_preserved")
        }
        NG2RuntimeTestHooks.deviceGeometry = { spare }
        check(!NG2DeviceGeometryBinding.local().legacyPassthrough, "host_fixture_only_local_override")
        NG2RuntimeTestHooks.deviceGeometry = nil
        print("PASS actual Runtime binding slice")
    }
}
