// Runs on the audio thread. Send mono samples to the page; output stays silent.
class DebateCapture extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]?.[0];
    if (input) this.port.postMessage(input.slice());
    return true;
  }
}
registerProcessor("debate-capture", DebateCapture);
