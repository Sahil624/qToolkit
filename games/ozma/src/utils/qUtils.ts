export function isCorrectBullet(isHadamardBullet: boolean, state: string): boolean {
    /**
     * Determines if a given projectile is the correct type to destroy an enemy,
     * based on the enemy's quantum state.
     *
     * Args:
     *   isHadamardBullet (boolean): True if the projectile is a Hadamard type, false if it's a Computational type.
     *   state (string): The current quantum state of the enemy ("|0>", "|1>", "|+>", "|->").
     *
     * Returns:
     *   boolean: True if the projectile is correct for the given quantum state, false otherwise.
     */
  
    if (isHadamardBullet) {
      // Hadamard projectiles are correct for superposition states
      return state === "|+>" || state === "|->";
    } else {
      // Computational projectiles are correct for computational states
      return state === "|0>" || state === "|1>";
    }
  }