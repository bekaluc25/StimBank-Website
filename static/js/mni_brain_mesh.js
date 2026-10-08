/**
 * mni_brain_mesh.js
 * Builds standard MNI152 / FreeSurfer fsaverage5 anatomical pial cortical surface meshes
 * (Left & Right Hemispheres with enhanced sulcal curvature, anatomical subcortical structures, and cerebellum)
 */

window.MNIBrainMeshBuilder = {
  /**
   * Transforms standard MNI coordinate [x, y, z] to Three.js coordinate [x, z, -y]
   * (MNI: +X=Right, +Y=Anterior, +Z=Superior -> Three.js: +X=Right, +Y=Up, -Z=Anterior)
   */
  mniToThree: function(x, y, z) {
    return new THREE.Vector3(x, z, -y);
  },

  /**
   * Build left and right cortical hemisphere meshes & subcortical structures
   */
  createHemispheres: function(options) {
    const opts = options || {};
    const glassOpacity = opts.opacity !== undefined ? opts.opacity : 0.35;

    const group = new THREE.Group();
    group.name = "brainGroup";

    // Build Left Hemisphere Geometry
    const leftGeom = this.buildHemisphereGeometry('left');
    // Build Right Hemisphere Geometry
    const rightGeom = this.buildHemisphereGeometry('right');

    // Cortical Surface Material (Translucent, crisp scientific glass/cortex)
    const createCortexMaterial = () => {
      return new THREE.MeshPhysicalMaterial({
        color: 0xF1F5F9,          // Crisp slate-white baseline
        vertexColors: true,       // High-contrast sulci vs gyri
        transparent: true,
        opacity: glassOpacity,
        roughness: 0.32,
        metalness: 0.08,
        transmission: 0.22,       // Refined translucent glass depth
        ior: 1.25,
        reflectivity: 0.7,
        depthWrite: false,
        side: THREE.DoubleSide
      });
    };

    const cortexMaterialLeft = createCortexMaterial();
    const cortexMaterialRight = createCortexMaterial();

    const leftMesh = new THREE.Mesh(leftGeom, cortexMaterialLeft);
    leftMesh.name = "leftHemisphere";
    group.add(leftMesh);

    const rightMesh = new THREE.Mesh(rightGeom, cortexMaterialRight);
    rightMesh.name = "rightHemisphere";
    group.add(rightMesh);

    // Subcortical Structures Group (Thalamus, Hippocampus, Basal Ganglia, Brainstem, Cerebellum)
    const subcorticalGroup = new THREE.Group();
    subcorticalGroup.name = "subcorticalGroup";

    const subMatThalamus = new THREE.MeshStandardMaterial({
      color: 0x93C5FD,        // Light Ice Blue
      transparent: true,
      opacity: Math.min(0.85, glassOpacity * 1.8),
      roughness: 0.4,
      metalness: 0.1,
      depthWrite: false
    });

    const subMatHippocampus = new THREE.MeshStandardMaterial({
      color: 0xA7F3D0,        // Soft Mint Green
      transparent: true,
      opacity: Math.min(0.85, glassOpacity * 1.8),
      roughness: 0.4,
      metalness: 0.1,
      depthWrite: false
    });

    const subMatBrainstem = new THREE.MeshStandardMaterial({
      color: 0xCBD5E1,        // Slate Grey
      transparent: true,
      opacity: Math.min(0.75, glassOpacity * 1.4),
      roughness: 0.5,
      depthWrite: false
    });

    const subMatCerebellum = new THREE.MeshStandardMaterial({
      color: 0xE2E8F0,        // Light Slate
      transparent: true,
      opacity: Math.min(0.55, glassOpacity * 1.1),
      roughness: 0.45,
      depthWrite: false
    });

    // 1. Thalamus (Left & Right)
    const thalGeom = new THREE.SphereGeometry(7.5, 20, 16);
    thalGeom.scale(1.0, 1.4, 1.2);
    
    const thalLeft = new THREE.Mesh(thalGeom, subMatThalamus);
    const thalPosL = this.mniToThree(-11, -16, 6);
    thalLeft.position.copy(thalPosL);
    thalLeft.name = "thalamusLeft";
    subcorticalGroup.add(thalLeft);

    const thalRight = new THREE.Mesh(thalGeom, subMatThalamus);
    const thalPosR = this.mniToThree(11, -16, 6);
    thalRight.position.copy(thalPosR);
    thalRight.name = "thalamusRight";
    subcorticalGroup.add(thalRight);

    // 2. Hippocampus / Amygdala (Left & Right Mesial Temporal)
    const hippoGeom = new THREE.CylinderGeometry(4.5, 3.5, 24, 16);
    hippoGeom.scale(1.0, 1.0, 0.75);
    hippoGeom.rotateX(Math.PI / 4);

    const hippoLeft = new THREE.Mesh(hippoGeom, subMatHippocampus);
    const hippoPosL = this.mniToThree(-25, -20, -14);
    hippoLeft.position.copy(hippoPosL);
    hippoLeft.name = "hippocampusLeft";
    subcorticalGroup.add(hippoLeft);

    const hippoRight = new THREE.Mesh(hippoGeom, subMatHippocampus);
    const hippoPosR = this.mniToThree(25, -20, -14);
    hippoRight.position.copy(hippoPosR);
    hippoRight.name = "hippocampusRight";
    subcorticalGroup.add(hippoRight);

    // 3. Brainstem (Pons & Medulla Core)
    const brainstemGeom = new THREE.CylinderGeometry(7.5, 5.5, 42, 20);
    const bsPos = this.mniToThree(0, -26, -34);
    brainstemGeom.translate(bsPos.x, bsPos.y, bsPos.z);
    const brainstemMesh = new THREE.Mesh(brainstemGeom, subMatBrainstem);
    brainstemMesh.name = "brainstem";
    subcorticalGroup.add(brainstemMesh);

    // 4. Cerebellum (Bilateral Posterior/Inferior lobes)
    const cerebGeomL = new THREE.SphereGeometry(24, 24, 18);
    cerebGeomL.scale(1.2, 0.8, 1.0);
    const cerebPosL = this.mniToThree(-24, -62, -36);
    cerebGeomL.translate(cerebPosL.x, cerebPosL.y, cerebPosL.z);
    const cerebMeshL = new THREE.Mesh(cerebGeomL, subMatCerebellum);
    cerebMeshL.name = "cerebellumLeft";
    subcorticalGroup.add(cerebMeshL);

    const cerebGeomR = new THREE.SphereGeometry(24, 24, 18);
    cerebGeomR.scale(1.2, 0.8, 1.0);
    const cerebPosR = this.mniToThree(24, -62, -36);
    cerebGeomR.translate(cerebPosR.x, cerebPosR.y, cerebPosR.z);
    const cerebMeshR = new THREE.Mesh(cerebGeomR, subMatCerebellum);
    cerebMeshR.name = "cerebellumRight";
    subcorticalGroup.add(cerebMeshR);

    group.add(subcorticalGroup);

    return {
      group: group,
      leftMesh: leftMesh,
      rightMesh: rightMesh,
      subcorticalGroup: subcorticalGroup,
      subMaterials: [subMatThalamus, subMatHippocampus, subMatBrainstem, subMatCerebellum],
      materials: [cortexMaterialLeft, cortexMaterialRight]
    };
  },

  /**
   * Build high-definition BufferGeometry from fsaverage5 MNI152 pial surface data
   */
  buildHemisphereGeometry: function(hemiKey) {
    const pialData = window.FSAVERAGE5_PIAL;
    if (pialData && pialData[hemiKey]) {
      const data = pialData[hemiKey];
      const rawVerts = data.vertices;
      const rawFaces = data.faces;
      const rawSulc = data.sulc;

      const numVerts = rawVerts.length / 3;
      const positions = new Float32Array(numVerts * 3);
      const colors = new Float32Array(numVerts * 3);

      for (let i = 0; i < numVerts; i++) {
        const mx = rawVerts[i * 3];
        const my = rawVerts[i * 3 + 1];
        const mz = rawVerts[i * 3 + 2];

        // Convert MNI [x, y, z] to Three.js space [x, z, -y]
        const v = this.mniToThree(mx, my, mz);
        positions[i * 3] = v.x;
        positions[i * 3 + 1] = v.y;
        positions[i * 3 + 2] = v.z;

        // Enhanced High-Contrast Sulcal Curvature Shading
        // s = 0 (Gyrus crest/ridge, bright) to 1 (Sulcus valley/groove, dark)
        const s = rawSulc ? rawSulc[i] : 0.5;
        // Non-linear contrast curve for crisp sulcal definition
        const contrastFactor = Math.pow(1.0 - s, 0.75); // 0.0 .. 1.0
        const brightness = 0.45 + contrastFactor * 0.55; // 0.45 .. 1.0

        // Cool scientific neutral tint with slight blue-grey depth
        colors[i * 3] = brightness * 0.92;     // R
        colors[i * 3 + 1] = brightness * 0.95; // G
        colors[i * 3 + 2] = brightness * 1.00; // B
      }

      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
      geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
      geometry.setIndex(rawFaces);
      geometry.computeVertexNormals();

      return geometry;
    }

    // Fallback parametric geometry
    return this.generateFallbackGeometry(hemiKey === 'left' ? -1 : 1);
  },

  generateFallbackGeometry: function(sign) {
    const geom = new THREE.SphereGeometry(45, 32, 24);
    geom.scale(sign * 0.9, 1.2, 1.4);
    const pos = this.mniToThree(sign * 32, -10, 15);
    geom.translate(pos.x, pos.y, pos.z);
    return geom;
  }
};
