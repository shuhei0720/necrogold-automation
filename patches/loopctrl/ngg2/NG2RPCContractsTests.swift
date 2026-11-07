// NecroGold NG-G2: real encrypted loopback RPC contracts, 2026-11-07.
// Fake execution handlers do not synthesize touches or prove iPhone behavior.
import CryptoKit
import Foundation
import Network
import XCTest

final class NG2RPCContractsTests: XCTestCase {
    private var server: JSONRPCServer!
    private var auth: AuthSession!
    private var client: URLSession!
    private var received: [(String, [String: JSONValue]?)] = []
    private let receivedLock = NSLock()

    override func setUpWithError() throws {
        try super.setUpWithError()
        RemoteSession.shared.setPaused(false)
        AuthManager.shared.armSingleAutoApproval()
        let paired = expectation(description: "one local test pairing")
        AuthManager.shared.requestAuth(clientName: "NG2 RPC contract " + UUID().uuidString,
            nearby: false, local: true) { outcome in
                if case .approved(let session) = outcome { self.auth = session }
                paired.fulfill()
            }
        wait(for: [paired], timeout: 5)
        _ = try XCTUnwrap(auth, "test pairing must mint an authenticated session")
        let port = UInt16.random(in: 20000...45000)
        server = JSONRPCServer(port: port, localOnly: true)
        let ready = expectation(description: "loopback listener ready")
        server.onStateChange = { if $0 { ready.fulfill() } }
        server.onRPCRequest = { method, params, complete in
            self.receivedLock.lock()
            self.received.append((method, params))
            self.receivedLock.unlock()
            complete(["method": .string(method), "owner": params?["_necro_owner"] ?? .null,
                      "actor": params?["_actor"] ?? .null], nil)
        }
        try server.start()
        wait(for: [ready], timeout: 5)
        let config = URLSessionConfiguration.ephemeral
        config.timeoutIntervalForRequest = 5
        config.timeoutIntervalForResource = 8
        client = URLSession(configuration: config)
    }

    override func tearDownWithError() throws {
        RemoteSession.shared.setPaused(false)
        server?.stop()
        client?.invalidateAndCancel()
        if let auth { AuthManager.shared.revokeSession(id: auth.id) }
        server = nil
        client = nil
        auth = nil
        try super.tearDownWithError()
    }

    private func encrypted(_ method: String, params: [String: Any] = [:],
                           session: AuthSession? = nil) throws -> (Data, Data, Data) {
        let identity = session ?? auth!
        let key = try XCTUnwrap(identity.key)
        let nonce = try XCTUnwrap(SecureEnvelope.randomBytes(16))
        let timestamp = UInt64(Date().timeIntervalSince1970)
        let plaintext = try JSONSerialization.data(withJSONObject: [
            "jsonrpc": "2.0", "id": 43, "method": method, "params": params])
        let cryptKey = SecureEnvelope.hmac(key, Data(SecureEnvelope.labelEncRequest.utf8) + nonce)
        let ciphertext = SecureEnvelope.keystreamXOR(key: cryptKey, nonce: nonce, data: plaintext)
        let tok = try XCTUnwrap(Data(hexString: identity.id))
        let macKey = SecureEnvelope.hmac(key, Data(SecureEnvelope.labelMac.utf8) + nonce)
        let tag = SecureEnvelope.hmac(macKey,
            Data("v1".utf8) + tok + SecureEnvelope.be64(timestamp) + nonce + ciphertext)
        let body = try JSONSerialization.data(withJSONObject: ["v": 1, "tok": identity.id,
            "ts": timestamp, "nonce": nonce.hexString, "ct": ciphertext.base64EncodedString(),
            "tag": tag.hexString])
        return (body, nonce, key)
    }

    private func request(_ body: Data, completion: @escaping (Data?, HTTPURLResponse?, Error?) -> Void) {
        var request = URLRequest(url: URL(string: "http://127.0.0.1:\(server.port)/rpc")!)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = body
        client.dataTask(with: request) { data, response, error in
            completion(data, response as? HTTPURLResponse, error)
        }.resume()
    }

    private func opened(_ raw: Data, nonce: Data, key: Data) throws -> [String: Any] {
        let envelope = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        XCTAssertEqual(envelope["nonce"] as? String, nonce.hexString)
        let ct = try XCTUnwrap((envelope["ct"] as? String).flatMap { Data(base64Encoded: $0) })
        let tag = try XCTUnwrap((envelope["tag"] as? String).flatMap(Data.init(hexString:)))
        let macKey = SecureEnvelope.hmac(key, Data(SecureEnvelope.labelMac.utf8) + nonce)
        XCTAssertTrue(SecureEnvelope.tagMatches(tag, message: Data("resp".utf8) + nonce + ct, key: macKey))
        let cryptKey = SecureEnvelope.hmac(key, Data(SecureEnvelope.labelEncResponse.utf8) + nonce)
        let data = SecureEnvelope.keystreamXOR(key: cryptKey, nonce: nonce, data: ct)
        return try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func rpc(_ method: String, params: [String: Any] = [:]) throws -> [String: Any] {
        let (body, nonce, key) = try encrypted(method, params: params)
        let reply = expectation(description: "encrypted " + method)
        var answer: [String: Any]?
        var failure: Error?
        request(body) { data, response, error in
            do {
                if let error { throw error }
                XCTAssertEqual(response?.statusCode, 200)
                answer = try self.opened(XCTUnwrap(data), nonce: nonce, key: key)
            } catch { failure = error }
            reply.fulfill()
        }
        wait(for: [reply], timeout: 8)
        if let failure { throw failure }
        return try XCTUnwrap(answer)
    }

    func testAuthenticatedOwnerProjectionUsesEnvelopeIdentityAtActualCallsite() throws {
        for method in ["necro_native_start", "necro_native_status", "necro_native_cancel", "necro_native_results"] {
            let response = try rpc(method, params: ["run_id": UUID().uuidString,
                "_necro_owner": "attacker", "_actor": ["tok": "attacker", "kind": "person"]])
            let result = try XCTUnwrap(response["result"] as? [String: Any])
            XCTAssertEqual(result["owner"] as? String, auth.id, "NG2_AUTHENTICATED_OWNER_CALLSITE")
            XCTAssertTrue(result["actor"] is NSNull, "native caller actor must be removed")
        }
        let plain = try rpc("logs", params: ["_necro_owner": "attacker"])
        let result = try XCTUnwrap(plain["result"] as? [String: Any])
        XCTAssertTrue(result["owner"] is NSNull, "owner projection is private to native methods")
    }

    func testOwnerPauseAllowsImageFreeStatusAndCancellationButRefusesStartAndResults() throws {
        RemoteSession.shared.setPaused(true)
        for method in ["necro_native_status", "necro_native_cancel"] {
            let response = try rpc(method, params: ["run_id": UUID().uuidString])
            XCTAssertNotNil(response["result"], method)
        }
        for method in ["necro_native_start", "necro_native_results"] {
            let response = try rpc(method, params: ["run_id": UUID().uuidString])
            let error = try XCTUnwrap(response["error"] as? [String: Any])
            XCTAssertEqual(error["code"] as? Int, -32003)
            let data = try XCTUnwrap(error["data"] as? [String: Any])
            XCTAssertEqual(data["outcome"] as? String, "not_sent")
        }
        receivedLock.lock()
        let methods = received.map { $0.0 }
        receivedLock.unlock()
        XCTAssertEqual(methods, ["necro_native_status", "necro_native_cancel"])
    }

    func testLeaseAdmissionRefusesUIAndCaptureBeforeDispatchWithoutBlockingStatus() throws {
        let refused: Set<String> = ["tap", "gesture", "screenshot", "run_steps"]
        server.onRPCLeaseCheck = { method in
            refused.contains(method) ? JSONRPCError(code: -32004, message: "native lease active",
                data: ["outcome": .string("not_sent"), "retry_safe": .bool(false)]) : nil
        }
        for method in refused.sorted() {
            let response = try rpc(method)
            XCTAssertEqual((response["error"] as? [String: Any])?["code"] as? Int, -32004)
        }
        XCTAssertNotNil(try rpc("necro_native_status")["result"])
        receivedLock.lock()
        let methods = received.map { $0.0 }
        receivedLock.unlock()
        XCTAssertEqual(methods, ["necro_native_status"])
    }

    func testUnauthenticatedPlaintextAndBadMACNeverReachLeaseOrExecution() throws {
        let leaseCalls = AtomicCounter()
        server.onRPCLeaseCheck = { _ in leaseCalls.increment(); return nil }
        let raw = try JSONSerialization.data(withJSONObject: ["jsonrpc": "2.0", "id": 1,
            "method": "necro_native_start", "params": ["_necro_owner": "attacker"]])
        let (valid, _, _) = try encrypted("necro_native_start")
        var damaged = try XCTUnwrap(JSONSerialization.jsonObject(with: valid) as? [String: Any])
        damaged["tag"] = String(repeating: "0", count: 64)
        for body in [raw, try JSONSerialization.data(withJSONObject: damaged)] {
            let denied = expectation(description: "unauthenticated request denied")
            request(body) { data, response, error in
                XCTAssertNil(error)
                XCTAssertEqual(response?.statusCode, 401)
                XCTAssertNotNil(data)
                denied.fulfill()
            }
            wait(for: [denied], timeout: 8)
        }
        XCTAssertEqual(leaseCalls.value, 0)
        receivedLock.lock()
        let count = received.count
        receivedLock.unlock()
        XCTAssertEqual(count, 0)
    }

    func testStatusRespondsWhileAnEarlierAsynchronousUIHandlerIsStillPending() throws {
        let uiStarted = expectation(description: "UI handler started")
        let uiReply = expectation(description: "held UI reply completed")
        let release = DispatchSemaphore(value: 0)
        let pending = AtomicCounter()
        server.onRPCRequest = { method, params, complete in
            if method == "tap" {
                pending.increment()
                uiStarted.fulfill()
                DispatchQueue.global().async {
                    _ = release.wait(timeout: .now() + 8)
                    complete(["held": .bool(true)], nil)
                }
            } else {
                XCTAssertEqual(pending.value, 1)
                complete(["owner": params?["_necro_owner"] ?? .null], nil)
            }
        }
        let (body, _, _) = try encrypted("tap")
        request(body) { _, response, error in
            XCTAssertNil(error)
            XCTAssertEqual(response?.statusCode, 200)
            uiReply.fulfill()
        }
        wait(for: [uiStarted], timeout: 5)
        defer { release.signal() }
        let status = try rpc("necro_native_status")
        XCTAssertNotNil(status["result"], "status must arrive before the pending UI completion is released")
        release.signal()
        wait(for: [uiReply], timeout: 5)
    }
}

private final class AtomicCounter {
    private let lock = NSLock()
    private var storage = 0
    func increment() { lock.lock(); storage += 1; lock.unlock() }
    var value: Int { lock.lock(); defer { lock.unlock() }; return storage }
}
