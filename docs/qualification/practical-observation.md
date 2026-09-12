# Practical Guide for Physical Connection, Observation, and Evidence Saving

## Purpose

This guide is an operational entry point for someone running a device-AP communication test for the first time: preparing it locally, starting it, stopping it, and saving the resulting evidence.
Use the product-specific procedure for product operations and acceptance criteria, and also satisfy the [common contract](README.md) for formal qualification.
This practical guide does not change the wire protocol, authentication requirements, or product acceptance criteria.

- [ ] Confirm the target, the Firmware in use, permitted operations, and stop conditions.
- [ ] Prepare one serial observer and a fresh evidence destination.
- [ ] Save the procedure, runtime, and start/abort/save commands locally before execution.
- [ ] Check human-wait limits, communication deadlines, total capture duration, and storage capacity separately.
- [ ] Ensure observation start, test start, and test end can be recorded separately.

## Preparation

Record the execution OS, runtime, destination filesystem, and how child processes are started and terminated.
When Windows owns the port, use a Windows-native runtime and a fresh destination on NTFS.
Before switching networks, perform a short test without the physical device to verify the actual save and stop path.
A test that uses only a virtual clock does not qualify the real clock or the actual save path.

The execution configuration should collect the target endpoint, source/build identity, input manifest, observer, product-specific validator,
start/abort/save commands, and each limit together with the result produced when that limit expires.
Manage required SHA values in the input manifest; do not duplicate hard-coded values across observers or product-specific helpers.
The observer records facts; the validator applies product-specific rules.

The test plan must identify the adopted D2B qualification-document revision by exact commit or an equivalent revision reference.
The [pre-SETUP budget declaration](physical-session-epochs.md#4-setup_epoch) applies to new qualification sessions that adopt a revision containing that requirement.
Do not retroactively reclassify historical test results or existing releases.
Adopting this document revision alone does not update the D2B input identity used to generate a Viewer bundle.

For development checks, an operator statement that no flash, OTA, or switch to another image occurred after the last verification may be used when accompanied by the type of supporting evidence and the verification time.
That statement is neither proof that no reset occurred during an unobserved interval nor exact-binary verification by readback.
Do not use that statement alone to replace candidate-identity verification required for formal qualification or release confirmation.

## Operation

| Order | Operation | Expected observation | If not satisfied |
| --- | --- | --- | --- |
| Before connection | Correlate the target's stable identity with the current port using the product procedure | Target is unique | Hold before starting if ambiguous |
| Start observation | Open the port with the single designated observer | Process is alive, port association is correct, and expected byte progress is observed | Stop duplicate monitors, reopen loops, or automatic reconnect; preserve the state |
| Preparation check | Save any boot/reset observed when the port was opened | Pre-test state is established | Do not infer whether an unobserved reset occurred |
| Join AP | Join the AP using the product procedure and confirm IP acquisition | Record association and IP separately | Treat as connection wait; do not start the communication test |
| Start test | Check remaining capture time and storage capacity, then record test start | Enough budget remains for the product test | Abort and save the attempt as an environment/setup limitation, not a product FAIL |
| Communication | Exercise HTTP fetch, WS connection, start, data, and normal stop in order | Result and timestamp remain for each layer | Follow the declared stop condition and record later steps as NOT RUN |

Reset behavior when opening a port varies by device, driver, and configuration.
Distinguish resets that occur during preparation from resets that occur during the test, and do not claim uninterrupted operation across unobserved intervals.
Predeclare quiet periods in which no acquisition is expected; process liveness alone does not establish healthy reception.

Do not reuse a short machine-response deadline for human preparation time.
For example, disabling a human-wait timeout does not create unlimited waiting when the total capture duration is 20 minutes: after 18 minutes of waiting to connect, only 2 minutes remain.
A 5-minute test cannot be started, and if the 20-minute limit is reached while waiting, the attempt ends because the outer capture limit expired.
Display or otherwise check remaining time and storage capacity before starting, and do not describe an operation as "unlimited" while finite outer limits still apply.
Decide any extension or separate capture generation before the test begins, and preserve earlier results.

After switching to the device AP, continued cloud-AI availability is not a prerequisite for continuing the test.
Proceed with the locally saved start command and use the prevalidated local abort command when needed.
Do not use forced termination as the normal abort path when it cannot guarantee orderly stop and saving.
There is no need to wait for cloud connectivity to return before classifying or saving the local result.

## Checking Results

Host UTC is a clock for ordering records across human review, host monotonic time measures elapsed time within the host, and device uptime measures elapsed time within the device.
Similar UTC and uptime deltas do not prove that observations came from the same uninterrupted boot.
Record observed boots, connection boundaries, and product-specific identity information together.

Check observer process liveness, byte progress, decode progress, and port changes separately.
Instead of having another process tail the active authoritative file, use process information, metadata such as file length, and counters exposed by the observer itself.
Search file contents only after the writer has finished.
Classify only the interval that was observed healthily, and do not treat successful saving as product qualification success.

## Failure Handling

Record observer failures, save failures, human-wait/resource limits, network departure, and product response violations as separate items.
If the reason cannot be determined, classify the result as INCONCLUSIVE; if an entry condition is missing, use HOLD; if a step was never started, use NOT RUN.
Use product FAIL only when a declared product requirement was actually exercised and not satisfied.
Successful response transmission and peer receipt are distinct observations; do not infer root cause from a close code or station reason alone.
When a retry is allowed, use a fresh destination and record the reason, changed conditions, and relationship to the earlier attempt.

## Finalization and Saving

Following the [existing evidence durability contract](evidence-generation-and-durability.md#7-finalization-order), keep these stages separate: stop new acquisition, finalize through the still-valid writable handle, and confirm process completion.

1. Stop initiating new test actions, and record the end and reason for the claim-bearing interval at the declared boundary.
   Observe normal stop and owner release through the declared deadlines and stop conditions; do not stop the observer early and cut off evidence needed for classification.
   Complete any permitted cleanup or recovery action whose result belongs to the same evidence generation, together with the recording of that result.
2. Request normal shutdown of the observer, stop new acquisition, and drain buffers within the predeclared scope.
   Do not substitute forced termination for normal shutdown.
3. While the streaming writer still holds the valid writable descriptor/handle, perform the flush/durability operation qualified for the target host, then close it.
   Do not attempt a new flush through a process that has already exited or a handle that has already been closed.
4. Confirm child-process and writer termination together with exit/finalization results, then finalize the result and observer summary.
   If a separate writer produces those files, complete its save, finalization, close, and termination checks as well.
   Preserve forced termination, flush failure, or a missing summary as incomplete evidence rather than repairing it in place.
5. Only after all target files are final, generate the inventory and checksum manifest, perform independent verification, record any required outer identity, and seal the generation in that order.
   Do not add substantive evidence after sealing.
   If evidence is copied, compare the finalized source inventory/identity with destination lengths and SHA-256 values.
   Do not treat a mismatch or partial copy as a completed identical copy.

If the design performs AP shutdown or restoration of host/device settings after sealing, predeclare that the result will be stored in a separate record outside the sealed generation or in a new evidence generation.
Any cleanup result that must belong to the same evidence generation must be completed in step 1 before finalization begins.
Map existing helpers to the stages above in the execution configuration; naming a host API alone does not qualify durability guarantees.

Making files read-only reduces accidental modification; it does not make evidence cryptographically immutable.
Do not paste authoritative raw evidence containing authentication values, stable device identifiers, private network names, personal paths, or school information into public documentation.
Publish only the necessary identifying hashes, compact result tables, and derived reports that state unperformed work explicitly.
Report HOST checks, build checks, and physical checks independently.
