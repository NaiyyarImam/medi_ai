"use client";

import React, { useState, useRef, Suspense, useEffect } from "react";
import { Canvas, useThree, useFrame } from "@react-three/fiber";
import { OrbitControls, useGLTF, OrbitControls as OrbitControlsType } from "@react-three/drei";
import * as THREE from "three";

type BodyZone = "Head" | "Chest" | "Abdomen" | "Arms" | "Legs" | null;

function SkeletonModel({ onBoneClick, onFocus }: {
  onBoneClick: (name: string) => void;
  onFocus: (position: THREE.Vector3) => void;
}) {
  const { scene } = useGLTF("/models/z_skeleton.glb");
  const selectedRef = useRef<THREE.Mesh | null>(null);

  React.useEffect(() => {
    scene.traverse((child: any) => {
      if (child.isMesh) {
        const mat = new THREE.MeshStandardMaterial({
          color: "#b79f82",
          roughness: 0.9,
          metalness: 0.1,
          emissive: new THREE.Color("#000000"),
          emissiveIntensity: 0,
        });
        child.material = mat;
        child.raycast = THREE.Mesh.prototype.raycast;
      }
    });
  }, [scene]);

  return (
    <primitive
      object={scene}
      dispose={null}
      onClick={(e: any) => {
        e.stopPropagation();

        let mesh: any = e.object;
        while (mesh && !mesh.isMesh) mesh = mesh.parent;
        if (!mesh || !mesh.material) return;

        // reset previous
        if (selectedRef.current) {
          const prevMaterial = selectedRef.current.material as THREE.MeshStandardMaterial;
          prevMaterial.emissive.set("#000000");
          prevMaterial.emissiveIntensity = 0;
        }

        // apply highlight
        const material = mesh.material as THREE.MeshStandardMaterial;
        material.emissive.set("#ff5500");
        material.emissiveIntensity = 2;

        selectedRef.current = mesh;

        const box = new THREE.Box3().setFromObject(mesh);
        const center = new THREE.Vector3();
        box.getCenter(center);

        onFocus(center);
        onBoneClick(mesh.name || "Unknown Bone");
      }}
    />
  );
}

function HumanModel() {
  const { scene } = useGLTF("/models/human.glb");
  return <primitive object={scene} scale={1.2} />;
}

function CameraController({
  target,
  controlsRef,
}: {
  target: THREE.Vector3 | null;
  controlsRef: React.RefObject<any>;
}) {
  const { camera } = useThree();

  useFrame(() => {
    if (!target || !controlsRef.current) return;

    // preserve current camera viewing direction
    const direction = new THREE.Vector3();
    camera.getWorldDirection(direction);

    // move camera toward selected bone while keeping same viewing side
    const desiredPosition = target
      .clone()
      .sub(direction.multiplyScalar(1.8));

    camera.position.lerp(desiredPosition, 0.08);

    // smoothly move orbit target instead of locking camera
    controlsRef.current.target.lerp(target.clone(), 0.08);
    controlsRef.current.update();
  });

  return null;
}

export default function AnatomyViewer({
  selected,
  onSelect,
}: {
  selected: BodyZone;
  onSelect: (zone: BodyZone) => void;
}) {
  const [boneName, setBoneName] = useState("");
  const [mode, setMode] = useState<"skeleton" | "human" | "organs">("skeleton");
  const [interactionMode, setInteractionMode] = useState<"symptom" | "explore">("symptom");
  const [cameraTarget, setCameraTarget] = useState<THREE.Vector3 | null>(null);
  const [boneInfo, setBoneInfo] = useState("");
  const controlsRef = useRef<any>(null);

  return (
    <div className="w-full h-[520px] bg-slate-900 rounded-xl relative">
      {/* Mode Switch */}
      <div className="absolute top-3 right-3 flex flex-col gap-3 z-10">
        <button onClick={() => setMode("skeleton")} className="px-3 py-1 bg-cyan-500 rounded">Skeleton</button>
        <button onClick={() => setMode("human")} className="px-3 py-1 bg-green-500 rounded">Human</button>
        <button onClick={() => setMode("organs")} className="px-3 py-1 bg-yellow-500 rounded">Organs</button>
      </div>

      {/* Interaction Mode */}
      <div className="flex gap-2 bg-black/40 p-2 rounded-xl border border-cyan-500/20">
        <button
          onClick={() => setInteractionMode("symptom")}
          className={`px-3 py-1 rounded-lg text-sm font-semibold transition ${
            interactionMode === "symptom"
              ? "bg-red-500 text-white"
              : "bg-slate-700 text-slate-200"
          }`}
        >
          🩺 Symptom Mode
        </button>

        <button
          onClick={() => setInteractionMode("explore")}
          className={`px-3 py-1 rounded-lg text-sm font-semibold transition ${
            interactionMode === "explore"
              ? "bg-cyan-500 text-black"
              : "bg-slate-700 text-slate-200"
          }`}
        >
          📚 Explore Mode
        </button>
      </div>

      <Canvas camera={{ position: [0, 1, 5], fov: 35 }}>
        <ambientLight intensity={1} />
        <directionalLight position={[2, 5, 2]} />

        <Suspense fallback={null}>
          {mode === "skeleton" && (
            <SkeletonModel
              onFocus={(pos) => setCameraTarget(pos)}
              onBoneClick={(name) => {
                setBoneName(name);

                const n = name.toLowerCase();

                let chatMessage = `I have pain near ${name}`;

                if (n.includes("skull") || n.includes("head")) {
                  chatMessage = "I have head pain";
                }
                else if (n.includes("rib") || n.includes("chest")) {
                  chatMessage = "I have chest pain";
                }
                else if (n.includes("spine")) {
                  chatMessage = "I have back pain";
                }
                else if (n.includes("arm") || n.includes("humerus")) {
                  chatMessage = "I have arm pain";
                }
                else if (n.includes("leg") || n.includes("femur")) {
                  chatMessage = "I have leg pain";
                }

                // 🔥 Only trigger AI in symptom mode
                if (interactionMode === "symptom") {
                  window.dispatchEvent(
                    new CustomEvent("anatomy-click", {
                      detail: chatMessage,
                    })
                  );
                }

                if (n.includes("skull") || n.includes("head")) {
                  onSelect("Head");
                  setBoneInfo("Skull protects the brain and supports facial structure.");
                }
                else if (n.includes("rib") || n.includes("chest")) {
                  onSelect("Chest");
                  setBoneInfo("Rib cage protects the heart and lungs.");
                }
                else if (n.includes("spine")) {
                  onSelect("Abdomen");
                  setBoneInfo("Spine supports posture and protects the spinal cord.");
                }
                else if (n.includes("arm") || n.includes("humerus")) {
                  onSelect("Arms");
                  setBoneInfo("Arm bones help movement and lifting.");
                }
                else if (n.includes("leg") || n.includes("femur")) {
                  onSelect("Legs");
                  setBoneInfo("Leg bones support body weight and movement.");
                }
                else {
                  setBoneInfo("Anatomical structure selected.");
                }
              }}
            />
          )}

          {mode === "human" && <HumanModel />}
        </Suspense>

        <CameraController target={cameraTarget} controlsRef={controlsRef} />
        <OrbitControls
          ref={controlsRef}
          makeDefault
          enablePan
          enableZoom
          enableRotate
          enableDamping
          dampingFactor={0.08}
          rotateSpeed={1.5}
          minPolarAngle={0}
          maxPolarAngle={Math.PI}
        />
      </Canvas>

      {/* Bone info card */}
      {boneName && (
        <div className="absolute top-4 left-4 bg-black/80 text-white px-4 py-3 rounded-xl border border-cyan-500 max-w-xs">
          <div className="text-cyan-300 font-semibold mb-1">
            🦴 {boneName}
          </div>

          <div className="text-sm text-gray-200">
            {boneInfo}
          </div>
        </div>
      )}

      {/* Organs placeholder */}
      {mode === "organs" && (
        <div className="absolute inset-0 flex items-center justify-center text-white text-xl">
          🧠 Organs Module Coming Soon
        </div>
      )}
    </div>
  );
}