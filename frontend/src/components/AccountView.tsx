"use client";
import {useEffect,useRef,useState,type FormEvent} from 'react';
import {isAxiosError} from 'axios';
import {useRouter} from 'next/navigation';
import Brand from '@/components/Brand';
import ProfileMenu from '@/components/ProfileMenu';
import Link from 'next/link';
import {ArrowLeftIcon} from '@/components/BackLink';
import api,{getCurrentUser,type UserResponse} from '@/services/api';
const roles={student:'Estudiante',teacher:'Docente',admin:'Administrador'};
export default function AccountView(){
 const router=useRouter();const [user,setUser]=useState<UserResponse|null>(null),[name,setName]=useState('');
 const [loading,setLoading]=useState(true),[loadError,setLoadError]=useState(false),[attempt,setAttempt]=useState(0);
 const [nameError,setNameError]=useState(''),[notice,setNotice]=useState(''),[passwordError,setPasswordError]=useState('');
 const [current,setCurrent]=useState(''),[password,setPassword]=useState(''),[confirmation,setConfirmation]=useState('');
 const [passwordOpen,setPasswordOpen]=useState(false);
 const [visible,setVisible]=useState({current:false,password:false,confirmation:false});
 const passwordTrigger=useRef<HTMLButtonElement>(null),currentInput=useRef<HTMLInputElement>(null);
 useEffect(()=>{if(passwordOpen)currentInput.current?.focus();},[passwordOpen]);
 const cleanedName=name.trim();const validName=cleanedName.length>0&&Array.from(cleanedName).length<=255;
 const [busy,setBusy]=useState(false);const locked=useRef(false);const nameInput=useRef<HTMLInputElement>(null);
 useEffect(()=>{if(!window.localStorage.getItem("token")){router.replace("/login");return;}let active=true;getCurrentUser().then(data=>{if(active){setUser(data);setName(data.name);setLoadError(false);setLoading(false);}}).catch(()=>{if(active){setLoadError(true);setLoading(false);}});return()=>{active=false;};},[attempt,router]);
 function failure(error:unknown){if(isAxiosError(error)&&typeof error.response?.data?.detail==='string')return error.response.data.detail;return 'No se pudo confirmar el guardado. Conservamos los campos para reintentar.';}
 async function saveName(event:FormEvent){event.preventDefault();if(locked.current||!user)return;setNameError('');setNotice('');const cleaned=name.trim();if(!cleaned||Array.from(cleaned).length>255){setNameError('Escribe un nombre de entre 1 y 255 caracteres.');nameInput.current?.focus();return;}if(cleaned===user.name)return;
  locked.current=true;setBusy(true);try{const {data}=await api.patch<UserResponse>('/auth/me',{name:cleaned});setUser(data);setName(data.name);setNotice('Nombre guardado.');window.dispatchEvent(new Event('biogamed:role-refresh'));}catch(error){setNameError(failure(error));}finally{locked.current=false;setBusy(false);}}
 async function savePassword(event:FormEvent){event.preventDefault();if(locked.current)return;setPasswordError('');const length=Array.from(password).length;if(!current||Array.from(current).length>255||length<8||length>255){setPasswordError('Introduce la contraseña actual y una nueva de entre 8 y 255 caracteres.');return;}if(password!==confirmation){setPasswordError('La nueva contraseña y su confirmación no coinciden.');return;}
  locked.current=true;setBusy(true);const token=window.localStorage.getItem('token');try{await api.post('/auth/me/password',{current_password:current,new_password:password,confirmation});setCurrent('');setPassword('');setConfirmation('');if(window.localStorage.getItem('token')===token)window.localStorage.removeItem('token');router.replace('/login?password=changed');}catch(error){setPasswordError(failure(error));}finally{locked.current=false;setBusy(false);}}
 return <div className="min-h-screen bg-background text-slate-900"><header className="site-header"><nav aria-label="Mi cuenta" className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-5 py-5"><Brand/><ProfileMenu name={user?.name}/></nav></header>
 <main className="mx-auto max-w-3xl space-y-4 px-5 py-5"><Link href="/dashboard" className="text-link inline-flex min-h-11 items-center gap-2 rounded-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"><ArrowLeftIcon/>Volver al panel</Link><h1 className="text-3xl font-black text-blue-950">Mi cuenta</h1>
 {loading&&<p role="status">Cargando tu cuenta…</p>}{loadError&&<div><p role="alert">No se pudo cargar tu cuenta. Si tu sesión ha caducado, inicia sesión de nuevo.</p><button type="button" className="button-secondary" onClick={()=>{setLoading(true);setAttempt(v=>v+1);}}>Reintentar</button></div>}
 {user&&!loadError&&<>
 <section className="rounded-2xl border border-slate-200 bg-white p-5" aria-labelledby="account-data-heading">
 <h2 id="account-data-heading" className="mb-3 text-xl font-bold text-blue-950">Datos de la cuenta</h2>
 <dl className="mb-4 grid gap-3 text-sm sm:grid-cols-2"><div><dt className="font-semibold">Correo electrónico</dt><dd className="break-all">{user.email}</dd></div><div><dt className="font-semibold">Rol</dt><dd>{roles[user.role]}</dd></div></dl>
 <form onSubmit={saveName} className="space-y-3" aria-label="Editar nombre">
 <div><label className="form-label" htmlFor="account-name">Nombre visible</label><input ref={nameInput} id="account-name" className="form-input" required autoComplete="name" value={name} disabled={busy} aria-invalid={!validName||!!nameError} aria-describedby={!validName||nameError?'account-name-error':undefined} onChange={e=>{setName(e.target.value);setNotice('');setNameError('');}}/></div>
 {(!validName||nameError)&&<p id="account-name-error" role="alert" className="notice-error">{nameError||'Escribe un nombre de entre 1 y 255 caracteres.'}</p>}{notice&&<p role="status" className="notice-success">{notice}</p>}
 <div className="flex flex-wrap gap-3"><button className="button-primary" disabled={busy||!validName||cleanedName===user.name}>Guardar</button><button type="button" className="button-secondary" disabled={busy} onClick={()=>{setName(user.name);setNameError('');setNotice('');nameInput.current?.focus();}}>Cancelar</button></div>
 </form></section>
 <section className="rounded-2xl border border-slate-200 bg-white p-5" aria-labelledby="account-security-heading">
 <h2 id="account-security-heading" className="mb-3 text-xl font-bold text-blue-950">Seguridad</h2>
 <h3 className="font-semibold">Contraseña</h3><p className="mb-3 text-sm text-slate-600">Puedes actualizar la contraseña que utilizas para acceder a BioGaMed.</p>
 <button ref={passwordTrigger} type="button" className="button-secondary" disabled={busy} aria-expanded={passwordOpen} aria-controls="account-password-form" onClick={()=>setPasswordOpen(v=>!v)} hidden={passwordOpen}>Cambiar contraseña</button>
 {passwordOpen&&<form id="account-password-form" onSubmit={savePassword} className="space-y-3" aria-label="Cambiar contraseña" aria-describedby="password-change-help password-length-help">
 <p id="password-change-help" className="notice-warning">Al cambiar la contraseña se cerrarán todas tus sesiones, incluida esta. Tendrás que iniciar sesión de nuevo</p>
 <p id="password-length-help" className="text-sm text-slate-600">Usa entre 8 y 255 caracteres.</p>
 {([
 {key:'current',id:'account-current',label:'Contraseña actual',value:current,set:setCurrent,autoComplete:'current-password'},
 {key:'password',id:'account-new',label:'Nueva contraseña',value:password,set:setPassword,autoComplete:'new-password'},
 {key:'confirmation',id:'account-confirm',label:'Confirmar nueva contraseña',value:confirmation,set:setConfirmation,autoComplete:'new-password'},
 ] as const).map(field=><div key={field.id}><label className="form-label" htmlFor={field.id}>{field.label}</label><div className="relative">
 <input ref={field.key==='current'?currentInput:undefined} id={field.id} className="form-input pr-14" type={visible[field.key]?'text':'password'} autoComplete={field.autoComplete} required value={field.value} disabled={busy} onChange={e=>field.set(e.target.value)}/>
 <button type="button" className="absolute right-1 top-1/2 flex min-h-11 min-w-11 -translate-y-1/2 items-center justify-center rounded-lg text-blue-900 hover:bg-sky-50 focus-visible:outline-2 focus-visible:outline-sky-700" disabled={busy} aria-controls={field.id} aria-pressed={visible[field.key]} aria-label={`${visible[field.key]?'Ocultar':'Mostrar'} ${field.key==='confirmation'?'confirmación de contraseña':field.label.toLocaleLowerCase('es')}`} onPointerDown={e=>e.preventDefault()} onClick={()=>setVisible(v=>({...v,[field.key]:!v[field.key]}))}>
 <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>{visible[field.key]&&<path d="m3 3 18 18"/>}</svg>
 </button></div></div>)}
 {passwordError&&<p role="alert" className="notice-error">{passwordError}</p>}
 <div className="flex flex-wrap gap-3"><button className="button-primary" disabled={busy}>Guardar nueva contraseña</button><button type="button" className="button-secondary" disabled={busy} onClick={()=>{setCurrent('');setPassword('');setConfirmation('');setPasswordError('');setVisible({current:false,password:false,confirmation:false});setPasswordOpen(false);requestAnimationFrame(()=>passwordTrigger.current?.focus());}}>Cancelar</button></div>
 </form>}
 </section></>}
 </main></div>;
}
