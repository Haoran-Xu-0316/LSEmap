/** Keep orbit inertia consistent across display rates and input-event frequency. */
export function useTimeBasedDamping(controls, now = () => performance.now()) {
  const responseAt60Hz = controls.dampingFactor;
  const update = controls.update.bind(controls);
  let previous = now();
  controls.update = (deltaTime = null) => {
    const current = now();
    // Bound a stalled/hidden frame without changing the eventual orbit angle.
    const elapsed = Math.min(0.1, Math.max(0, (current - previous) / 1000));
    previous = current;
    controls.dampingFactor = 1 - Math.pow(1 - responseAt60Hz, elapsed * 60);
    return update(deltaTime);
  };
}

/** Clear residual orbit/pan input while preserving the current visible pose. */
export function stopControlInertia(controls) {
  const position = controls.object.position.clone();
  const target = controls.target.clone();
  const damping = controls.enableDamping;
  controls.enableDamping = false;
  controls.update();
  controls.object.position.copy(position);
  controls.target.copy(target);
  controls.update();
  controls.enableDamping = damping;
}
