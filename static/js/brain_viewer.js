/**
 * brain_viewer.js
 * Interactive 3D MNI Brain Viewer for StimBank
 * Adheres to the "Quiet interface, colorful data" design philosophy
 */

class EBSBrainViewer {
  constructor(containerId, options) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error("Container element not found:", containerId);
      return;
    }

    this.options = options || {};
    this.sites = [];
    this.siteMeshes = [];
    this.activeSite = null;
    this.colorMode = 'category';
    
    // StimBank 5 Standard Categories of Phenomena
    this.categoryColors = {
      "Sensory & Perceptual": 0x0284C7,  // Cerulean / Sky (#0284C7)
      "Affective": 0xE11D48,             // Crimson / Rose (#E11D48)
      "Autonomic": 0x059669,             // Emerald Green (#059669)
      "Cognitive & Language": 0x8B5CF6,  // Violet / Purple (#8B5CF6)
      "Motor": 0x2563EB,                 // Royal Motor Blue (#2563EB)
      // Backward compatibility aliases
      "Somatosensory": 0x0284C7,
      "Visual": 0x0284C7,
      "Auditory": 0x0284C7,
      "Language/Speech": 0x8B5CF6,
      "Cognitive/Memory": 0x8B5CF6,
      "Affective/Emotional": 0xE11D48
    };

    // Pathology Color Palette (Muted scientific data tones)
    this.pathologyColors = {
      "Refractory Focal Epilepsy": 0x2E68A8,
      "Drug-resistant Temporal Lobe Epilepsy": 0x2E68A8,
      "Drug-resistant Partial Epilepsy": 0x2E68A8,
      "Drug-resistant Focal Epilepsy": 0x2E68A8,
      "Pharmaco-resistant Epilepsy": 0x2E68A8,
      "Mesial Temporal Lobe Epilepsy": 0x2E68A8,
      "Refractory Complex Partial Epilepsy": 0x2E68A8,
      "Intractable Epilepsy": 0x2E68A8,
      "Epilepsy Presurgical Evaluation": 0x2E68A8,
      "Low-grade Glioma (WHO II)": 0x498259,
      "High-grade Glioma (WHO IV)": 0x3D6F4B,
      "Diffuse Low-grade Gliomas": 0x498259,
      "Brain Neoplasms (Glioma)": 0x498259,
      "Brain Tumor & Epilepsy": 0x318282,
      "Parkinson's Disease": 0xC06526,
      "Idiopathic Parkinson's Disease": 0xC06526,
      "Parkinson's Disease & Essential Tremor": 0xC06526,
      "Essential Tremor": 0xB5571E,
      "Treatment-resistant Major Depression": 0xA13448,
      "Severe Obsessive-Compulsive Disorder": 0x725FA2,
      "Severe Intractable Tinnitus": 0x3C7F9F,
      "Chronic Neuropathic Pain": 0x8C3345
    };

    // Procedure Color Palette
    this.procedureColors = {
      "Stereo-EEG (sEEG)": 0x2E68A8,
      "Subdural ECoG Grid/Strip": 0x725FA2,
      "Intraoperative Direct Electrical Stimulation (DES)": 0xC06526,
      "Deep Brain Stimulation (DBS)": 0xA13448
    };

    this.initScene();
    this.initLights();
    this.initBrainModel();
    this.initRaycaster();
    this.initEventListeners();
    this.animate();
  }

  initScene() {
    this.width = this.container.clientWidth;
    this.height = this.container.clientHeight;

    this.scene = new THREE.Scene();
    // Clean neutral scientific canvas background (#FAFAFA)
    this.scene.background = new THREE.Color(0xFAFAFA);

    // Subtle coordinate orientation helper
    const axes = new THREE.AxesHelper(25);
    axes.position.set(-75, -55, -75);
    this.scene.add(axes);

    this.camera = new THREE.PerspectiveCamera(45, this.width / this.height, 1, 2000);
    this.setCameraPreset('isometric');

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.container.appendChild(this.renderer.domElement);

    // OrbitControls
    if (typeof THREE.OrbitControls !== 'undefined') {
      this.controls = new THREE.OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.06;
      this.controls.minDistance = 60;
      this.controls.maxDistance = 600;
      this.controls.target.set(0, 10, 0);
    }
  }

  initLights() {
    // Soft, diffused ambient illumination
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.95);
    this.scene.add(ambientLight);

    // Key Light
    const keyLight = new THREE.DirectionalLight(0xfffdfa, 0.9);
    keyLight.position.set(120, 180, 150);
    this.scene.add(keyLight);

    // Soft fill Light
    const fillLight = new THREE.DirectionalLight(0xf2ede4, 0.6);
    fillLight.position.set(-150, -80, -120);
    this.scene.add(fillLight);
  }

  initBrainModel() {
    this.brainParts = window.MNIBrainMeshBuilder.createHemispheres({
      opacity: 0.28
    });
    this.scene.add(this.brainParts.group);

    this.sitesGroup = new THREE.Group();
    this.sitesGroup.name = "sitesGroup";
    this.scene.add(this.sitesGroup);
  }

  initRaycaster() {
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.hoveredMesh = null;
    this.tooltip = document.getElementById('brainTooltip');
  }

  setSites(sites) {
    this.sites = sites || [];
    this.rebuildSiteSpheres();
  }

  getColorForSite(site) {
    if (this.colorMode === 'pathology') {
      return this.pathologyColors[site.pathology] || 0x2E68A8;
    } else if (this.colorMode === 'procedure') {
      return this.procedureColors[site.procedure] || 0xC06526;
    } else {
      return this.categoryColors[site.category] || 0x2E68A8;
    }
  }

  rebuildSiteSpheres() {
    while (this.sitesGroup.children.length > 0) {
      const obj = this.sitesGroup.children[0];
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
      this.sitesGroup.remove(obj);
    }
    this.siteMeshes = [];

    const sphereGeom = new THREE.SphereGeometry(3.0, 24, 20);

    this.sites.forEach(site => {
      const col = this.getColorForSite(site);
      const mat = new THREE.MeshStandardMaterial({
        color: col,
        roughness: 0.2,
        metalness: 0.1
      });

      const mesh = new THREE.Mesh(sphereGeom, mat);
      const pos = window.MNIBrainMeshBuilder.mniToThree(site.mni[0], site.mni[1], site.mni[2]);
      mesh.position.copy(pos);
      mesh.userData.site = site;
      mesh.userData.originalColor = col;
      mesh.userData.originalScale = 1.0;

      this.sitesGroup.add(mesh);
      this.siteMeshes.push(mesh);
    });

    this.updateHUDStats();
  }

  updateColors() {
    this.siteMeshes.forEach(mesh => {
      const col = this.getColorForSite(mesh.userData.site);
      mesh.material.color.setHex(col);
      mesh.userData.originalColor = col;
    });
  }

  setColorMode(mode) {
    this.colorMode = mode;
    this.updateColors();
  }

  filterSites(predicate) {
    let visibleCount = 0;
    this.siteMeshes.forEach(mesh => {
      const match = predicate(mesh.userData.site);
      mesh.visible = match;
      if (match) visibleCount++;
    });
    this.updateHUDStats(visibleCount);
  }

  highlightSite(siteId) {
    this.siteMeshes.forEach(mesh => {
      if (mesh.userData.site.id === siteId) {
        mesh.scale.set(2.2, 2.2, 2.2);
        mesh.material.color.setHex(0x111111); // dark charcoal highlight outline
        if (this.controls) {
          this.controls.target.copy(mesh.position);
        }
      } else {
        mesh.scale.set(1.0, 1.0, 1.0);
        mesh.material.color.setHex(mesh.userData.originalColor);
      }
    });
  }

  resetHighlights() {
    this.siteMeshes.forEach(mesh => {
      mesh.scale.set(1.0, 1.0, 1.0);
      mesh.material.color.setHex(mesh.userData.originalColor);
    });
  }

  setHemisphereVisibility(mode) {
    if (!this.brainParts) return;
    if (mode === 'both') {
      this.brainParts.leftMesh.visible = true;
      this.brainParts.rightMesh.visible = true;
    } else if (mode === 'left') {
      this.brainParts.leftMesh.visible = true;
      this.brainParts.rightMesh.visible = false;
    } else if (mode === 'right') {
      this.brainParts.leftMesh.visible = false;
      this.brainParts.rightMesh.visible = true;
    }
  }

  setGlassOpacity(val) {
    if (!this.brainParts) return;
    this.brainParts.materials.forEach(mat => {
      mat.opacity = parseFloat(val);
      mat.depthWrite = parseFloat(val) > 0.8;
    });
  }

  setCameraPreset(preset) {
    const dist = 240;
    const targetY = 12;

    if (preset === 'left') {
      this.camera.position.set(-dist, targetY, 0);
    } else if (preset === 'right') {
      this.camera.position.set(dist, targetY, 0);
    } else if (preset === 'superior') {
      this.camera.position.set(0, dist + 20, 0.1);
    } else if (preset === 'anterior') {
      this.camera.position.set(0, targetY, dist);
    } else if (preset === 'posterior') {
      this.camera.position.set(0, targetY, -dist);
    } else if (preset === 'inferior') {
      this.camera.position.set(0, -dist - 20, 0.1);
    } else {
      this.camera.position.set(180, 140, 190);
    }

    if (this.controls) {
      this.controls.target.set(0, targetY, 0);
      this.controls.update();
    }
  }

  updateHUDStats(count) {
    const total = this.siteMeshes.length;
    const current = count !== undefined ? count : this.siteMeshes.filter(m => m.visible).length;
    const countEl = document.getElementById('viewerSiteCount');
    if (countEl) {
      countEl.innerText = `${current} / ${total} sites`;
    }
  }

  initEventListeners() {
    window.addEventListener('resize', () => this.onWindowResize());
    this.container.addEventListener('mousemove', (e) => this.onMouseMove(e));
    this.container.addEventListener('click', (e) => this.onClick(e));
    this.container.addEventListener('mouseleave', () => this.hideTooltip());
  }

  onWindowResize() {
    if (!this.container) return;
    this.width = this.container.clientWidth;
    this.height = this.container.clientHeight;
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(this.width, this.height);
  }

  onMouseMove(e) {
    const rect = this.container.getBoundingClientRect();
    this.mouse.x = ((e.clientX - rect.left) / this.width) * 2 - 1;
    this.mouse.y = -((e.clientY - rect.top) / this.height) * 2 + 1;

    this.raycaster.setFromCamera(this.mouse, this.camera);
    const visibleMeshes = this.siteMeshes.filter(m => m.visible);
    const intersects = this.raycaster.intersectObjects(visibleMeshes);

    if (intersects.length > 0) {
      const topIntersect = intersects[0];
      const mesh = topIntersect.object;
      const site = mesh.userData.site;

      if (this.hoveredMesh !== mesh) {
        if (this.hoveredMesh) {
          this.hoveredMesh.scale.set(1.0, 1.0, 1.0);
        }
        this.hoveredMesh = mesh;
        mesh.scale.set(1.5, 1.5, 1.5);
        this.container.style.cursor = 'pointer';
      }

      this.showTooltip(e, site);
    } else {
      if (this.hoveredMesh) {
        this.hoveredMesh.scale.set(1.0, 1.0, 1.0);
        this.hoveredMesh = null;
        this.container.style.cursor = 'default';
      }
      this.hideTooltip();
    }
  }

  onClick(e) {
    if (this.hoveredMesh) {
      const site = this.hoveredMesh.userData.site;
      this.openSiteDetailModal(site);
    }
  }

  showTooltip(e, site) {
    if (!this.tooltip) return;
    const rect = this.container.getBoundingClientRect();
    const x = e.clientX - rect.left + 15;
    const y = e.clientY - rect.top + 15;

    this.tooltip.style.left = `${x}px`;
    this.tooltip.style.top = `${y}px`;
    this.tooltip.style.display = 'block';

    const hex = this.categoryColors[site.category] || 0x2E68A8;
    const colorHexStr = '#' + hex.toString(16).padStart(6, '0');

    this.tooltip.innerHTML = `
      <div style="font-weight:700; color:#252525; margin-bottom:4px; font-size:0.9rem;">${site.region}</div>
      <div style="margin-bottom:6px;">
        <span class="cat-badge" style="border-left:3px solid ${colorHexStr};">
          <span class="category-dot" style="background-color:${colorHexStr};"></span>
          ${site.category}
        </span>
      </div>
      <div style="font-weight:500; color:#252525; margin-bottom:4px;">${site.effect}</div>
      <div style="color:#77736C; font-size:0.75rem;">MNI: [${site.mni.join(', ')}] mm</div>
      <div style="color:#77736C; font-size:0.75rem; margin-top:2px;">${site.pathology} &bull; ${site.procedure}</div>
      <div style="color:#252525; font-size:0.72rem; margin-top:8px; border-top:1px solid #E5E7EB; padding-top:4px;">
        Click to inspect clinical details
      </div>
    `;
  }

  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  openSiteDetailModal(site) {
    const modalEl = document.getElementById('siteDetailModal');
    if (!modalEl) return;

    document.getElementById('modalSiteId').innerText = site.id;
    document.getElementById('modalRegion').innerText = `${site.region} (${site.hemisphere === 'L' ? 'Left' : 'Right'} Hemisphere)`;
    document.getElementById('modalMni').innerText = `X: ${site.mni[0]}, Y: ${site.mni[1]}, Z: ${site.mni[2]} mm`;
    document.getElementById('modalEffect').innerText = site.effect;
    
    const catBadge = document.getElementById('modalCategoryBadge');
    if (catBadge) {
      const hex = this.categoryColors[site.category] || 0x2E68A8;
      const colorHexStr = '#' + hex.toString(16).padStart(6, '0');
      catBadge.className = 'cat-badge';
      catBadge.innerHTML = `<span class="category-dot" style="background-color:${colorHexStr};"></span>${site.category}`;
    }

    document.getElementById('modalPathology').innerText = site.pathology;
    document.getElementById('modalProcedure').innerText = site.procedure;
    document.getElementById('modalStimParams').innerText = `${site.frequency_hz} Hz, ${site.current_ma} mA, ${site.pulse_width_ms} ms (${site.bipolar ? 'Bipolar' : 'Monopolar'})`;
    document.getElementById('modalPatient').innerText = `${site.patient_age} yrs, ${site.patient_sex === 'M' ? 'Male' : 'Female'}`;

    if (site.publication) {
      document.getElementById('modalPaperTitle').innerText = site.publication.title;
      document.getElementById('modalPaperAuthors').innerText = site.publication.authors;
      document.getElementById('modalPaperJournal').innerText = `${site.publication.journal} (${site.publication.year}) — ${site.publication.country}`;
      const doiLink = document.getElementById('modalPaperLink');
      if (doiLink) {
        doiLink.href = `https://doi.org/${site.publication.doi}`;
        doiLink.innerText = `DOI: ${site.publication.doi}`;
      }
    }

    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
      const modal = new bootstrap.Modal(modalEl);
      modal.show();
    }
  }

  animate() {
    requestAnimationFrame(() => this.animate());
    if (this.controls) this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}

window.EBSBrainViewer = EBSBrainViewer;
