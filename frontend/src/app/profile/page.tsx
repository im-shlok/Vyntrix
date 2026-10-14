'use client';

import React, { FormEvent, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import {
  ArrowLeft,
  CheckCircle2,
  Droplets,
  Save,
  User,
  Waves
} from 'lucide-react';

type ProfileForm = {
  farmer_name: string;
  contact_number: string;
  location: string;
  address: string;
  current_crop: string;
  land_size_hectares: string;
  soil_type: string;
  irrigation_type: string;
  budget: string;
};

type TelemetryForm = {
  soil_moisture: string;
  soil_ph: string;
  nitrogen: string;
  phosphorus: string;
  potassium: string;
};

const defaultProfile: ProfileForm = {
  farmer_name: '',
  contact_number: '',
  location: '',
  address: '',
  current_crop: 'Tomato',
  land_size_hectares: '1.5',
  soil_type: 'Loam',
  irrigation_type: 'Drip',
  budget: 'Medium'
};

const defaultTelemetry: TelemetryForm = {
  soil_moisture: '48',
  soil_ph: '6.7',
  nitrogen: '178',
  phosphorus: '41',
  potassium: '215'
};

const inputClass = 'w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/30';
const labelClass = 'mb-1.5 block text-[9px] font-mono font-bold uppercase tracking-widest text-zinc-500';

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<ProfileForm>(defaultProfile);
  const [telemetry, setTelemetry] = useState<TelemetryForm>(defaultTelemetry);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const currentSession = localStorage.getItem('kisaan_session');
    if (!currentSession) {
      router.push('/auth');
      return;
    }

    const storedProfile = localStorage.getItem(`kisaan_user_${currentSession}`);
    if (storedProfile) {
      const parsed = JSON.parse(storedProfile);
      Promise.resolve().then(() => {
        setProfile((current) => ({
          ...current,
          ...Object.fromEntries(Object.keys(current).map((key) => [key, parsed[key] ?? current[key as keyof ProfileForm]]))
        }));
      });
    }

    fetch('http://localhost:8000/api/iot/telemetry')
      .then((response) => {
        if (!response.ok) throw new Error('Telemetry unavailable');
        return response.json();
      })
      .then((data) => setTelemetry({
        soil_moisture: String(data.soil_moisture ?? defaultTelemetry.soil_moisture),
        soil_ph: String(data.soil_ph ?? defaultTelemetry.soil_ph),
        nitrogen: String(data.nitrogen ?? defaultTelemetry.nitrogen),
        phosphorus: String(data.phosphorus ?? defaultTelemetry.phosphorus),
        potassium: String(data.potassium ?? defaultTelemetry.potassium)
      }))
      .catch(() => setStatus({ type: 'error', text: 'Could not load current telemetry values.' }))
      .finally(() => setLoading(false));
  }, [router]);

  const updateProfile = (key: keyof ProfileForm, value: string) => {
    setProfile((current) => ({ ...current, [key]: value }));
  };

  const updateTelemetry = (key: keyof TelemetryForm, value: string) => {
    setTelemetry((current) => ({ ...current, [key]: value }));
  };

  const saveChanges = async (event: FormEvent) => {
    event.preventDefault();
    const session = localStorage.getItem('kisaan_session');
    if (!session) return;
    setSaving(true);
    setStatus(null);

    const numericTelemetry = Object.fromEntries(
      Object.entries(telemetry).map(([key, value]) => [key, Number(value)])
    );

    if (Object.values(numericTelemetry).some((value) => !Number.isFinite(value))) {
      setStatus({ type: 'error', text: 'Enter valid numbers for all soil readings.' });
      setSaving(false);
      return;
    }

    const profileKey = `kisaan_user_${session}`;
    const existingProfile = JSON.parse(localStorage.getItem(profileKey) || '{}');
    const updatedProfile = {
      ...existingProfile,
      ...profile,
      ph: numericTelemetry.soil_ph,
      land_size_hectares: Number(profile.land_size_hectares)
    };

    localStorage.setItem(profileKey, JSON.stringify(updatedProfile));

    try {
      const response = await fetch('http://localhost:8000/api/iot/telemetry', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(numericTelemetry)
      });
      if (!response.ok) {
        const error = await response.json().catch(() => null);
        throw new Error(error?.detail || 'Telemetry update failed');
      }

      setStatus({ type: 'success', text: 'Profile and soil telemetry saved successfully.' });
    } catch (error) {
      setStatus({
        type: 'error',
        text: `Farmer profile saved, but telemetry could not be updated: ${error instanceof Error ? error.message : 'unknown error'}`
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <main className="min-h-screen bg-[#020503] p-8 font-mono text-xs text-emerald-400">Loading farmer profile...</main>;
  }

  return (
    <main className="min-h-screen bg-[#020503] px-4 py-6 text-zinc-200 md:px-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-6 flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/dashboard')} className="rounded-xl border border-white/10 p-2 text-zinc-400 transition hover:border-emerald-500/40 hover:text-emerald-400" aria-label="Back to dashboard">
              <ArrowLeft size={16} />
            </button>
            <div>
              <div className="flex items-center gap-3">
                <Image src="/logo.png" alt="Agriva logo" width={112} height={32} className="h-8 w-auto object-contain" priority />
                <span className="font-mono text-[10px] font-bold uppercase tracking-[0.25em] text-emerald-400">[FARMER_PROFILE]</span>
              </div>
              <h1 className="mt-1 text-xl font-black text-white">Edit Farm Profile</h1>
            </div>
          </div>
          <span className="hidden rounded-full border border-emerald-500/20 bg-emerald-500/5 px-3 py-1.5 text-[9px] font-mono uppercase tracking-widest text-emerald-400 sm:block">Agriva Node Active</span>
        </header>

        <form onSubmit={saveChanges} className="space-y-5">
          <section className="rounded-3xl border border-white/10 bg-white/[0.02] p-5 shadow-2xl md:p-7">
            <div className="mb-5 flex items-center gap-3 border-b border-white/10 pb-4">
              <User className="text-emerald-400" size={18} />
              <div>
                <h2 className="text-sm font-bold text-white">Farmer and Farm Details</h2>
                <p className="text-[10px] text-zinc-500">Update information used for personalized recommendations.</p>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <label><span className={labelClass}>Farmer name</span><input className={inputClass} value={profile.farmer_name} onChange={(e) => updateProfile('farmer_name', e.target.value)} required /></label>
              <label><span className={labelClass}>Contact number</span><input className={inputClass} value={profile.contact_number} onChange={(e) => updateProfile('contact_number', e.target.value)} /></label>
              <label><span className={labelClass}>Village / location</span><input className={inputClass} value={profile.location} onChange={(e) => updateProfile('location', e.target.value)} required /></label>
              <label><span className={labelClass}>Address</span><input className={inputClass} value={profile.address} onChange={(e) => updateProfile('address', e.target.value)} /></label>
              <label><span className={labelClass}>Current crop</span><input className={inputClass} value={profile.current_crop} onChange={(e) => updateProfile('current_crop', e.target.value)} required /></label>
              <label><span className={labelClass}>Land size (hectares)</span><input className={inputClass} type="number" min="0" step="0.01" value={profile.land_size_hectares} onChange={(e) => updateProfile('land_size_hectares', e.target.value)} required /></label>
              <label><span className={labelClass}>Soil type</span><select className={inputClass} value={profile.soil_type} onChange={(e) => updateProfile('soil_type', e.target.value)}><option>Loam</option><option>Sandy Loam</option><option>Clay Loam</option><option>Alluvial</option><option>Black Soil</option></select></label>
              <label><span className={labelClass}>Irrigation method</span><select className={inputClass} value={profile.irrigation_type} onChange={(e) => updateProfile('irrigation_type', e.target.value)}><option>Drip</option><option>Sprinkler</option><option>Flood</option><option>Rainfed</option></select></label>
              <label><span className={labelClass}>Input budget</span><select className={inputClass} value={profile.budget} onChange={(e) => updateProfile('budget', e.target.value)}><option>Low</option><option>Medium</option><option>High</option></select></label>
            </div>
          </section>

          <section className="rounded-3xl border border-cyan-500/15 bg-cyan-950/[0.08] p-5 shadow-2xl md:p-7">
            <div className="mb-5 flex items-center gap-3 border-b border-white/10 pb-4">
              <Droplets className="text-cyan-400" size={18} />
              <div>
                <h2 className="text-sm font-bold text-white">Soil Telemetry</h2>
                <p className="text-[10px] text-zinc-500">Enter the latest readings from a soil test or field sensor.</p>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <label><span className={labelClass}>Moisture %</span><input className={inputClass} type="number" min="0" max="100" step="0.1" value={telemetry.soil_moisture} onChange={(e) => updateTelemetry('soil_moisture', e.target.value)} required /></label>
              <label><span className={labelClass}>Soil pH</span><input className={inputClass} type="number" min="0" max="14" step="0.1" value={telemetry.soil_ph} onChange={(e) => updateTelemetry('soil_ph', e.target.value)} required /></label>
              <label><span className={labelClass}>Nitrogen</span><input className={inputClass} type="number" min="0" step="0.1" value={telemetry.nitrogen} onChange={(e) => updateTelemetry('nitrogen', e.target.value)} required /></label>
              <label><span className={labelClass}>Phosphorus</span><input className={inputClass} type="number" min="0" step="0.1" value={telemetry.phosphorus} onChange={(e) => updateTelemetry('phosphorus', e.target.value)} required /></label>
              <label><span className={labelClass}>Potassium</span><input className={inputClass} type="number" min="0" step="0.1" value={telemetry.potassium} onChange={(e) => updateTelemetry('potassium', e.target.value)} required /></label>
            </div>
            <div className="mt-4 flex items-start gap-2 text-[10px] leading-relaxed text-zinc-500"><Waves size={13} className="mt-0.5 shrink-0 text-cyan-400" />Temperature and humidity remain sensor-managed. Update them only through the connected telemetry device.</div>
          </section>

          {status && <div className={`flex items-center gap-2 rounded-2xl border px-4 py-3 text-xs ${status.type === 'success' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-red-500/30 bg-red-500/10 text-red-300'}`}>{status.type === 'success' && <CheckCircle2 size={15} />}{status.text}</div>}

          <div className="flex flex-col-reverse justify-between gap-3 sm:flex-row">
            <button type="button" onClick={() => router.push('/dashboard')} className="rounded-xl border border-white/10 px-5 py-3 text-xs font-bold text-zinc-400 transition hover:border-white/20 hover:text-white">Cancel</button>
            <button type="submit" disabled={saving} className="flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-6 py-3 text-xs font-black text-black transition hover:bg-emerald-400 disabled:cursor-wait disabled:opacity-60"><Save size={15} />{saving ? 'Saving...' : 'Save profile and telemetry'}</button>
          </div>
        </form>
      </div>
    </main>
  );
}
