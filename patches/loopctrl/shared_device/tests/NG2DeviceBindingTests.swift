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
        check(p8.pointee.qualification_gaps == 31 && p8.pointee.lab_input_permitted == 1, "lab_permission_keeps_gap31_unaccepted")
        let mapped=spare.resolvedPoint(command)
        check(mapped?.x == 187.5 && mapped?.y == 40, "Double_halfpoint_preserved")
        var closedFixture = p8.pointee
        closedFixture.lab_input_permitted = 0
        withUnsafePointer(to: &closedFixture) { pointer in
            let fixture = NG2DeviceGeometryBinding(profile:pointer, panelWidth:375, panelHeight:667, model:"iPhone10,1")
            check(fixture.resolvedPoint(command) == nil, "gap31_closed_before_begin")
        }
        check("unknown".withCString { ng2_device_geometry_profile($0,375,667) } == nil, "unknown_model_rejected")
        let unknown = NG2DeviceGeometryBinding(profile:nil, panelWidth:375, panelHeight:667, model:"unknown")
        check(unknown.resolvedPoint(command) == nil, "unknown_profile_rejected")
        command.direction=0
        check(spare.resolvedPoint(command) == nil, "unknown_direction_rejected")
        command.kind=99
        check(spare.resolvedPoint(command) == nil, "unknown_action_rejected")
        NG2RuntimeTestHooks.deviceGeometry = { spare }
        check(!NG2DeviceGeometryBinding.local().legacyPassthrough, "host_fixture_only_local_override")
        NG2RuntimeTestHooks.deviceGeometry = nil
        print("PASS actual Runtime binding slice")
    }
}
