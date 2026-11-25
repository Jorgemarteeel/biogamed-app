import Image from "next/image";
import Link from "next/link";
import styles from "./DashboardGames.module.css";

export default function DashboardGames() {
  return <div className={styles.games}>
    <article className={styles.card} aria-labelledby="dashboard-pasapalabra-title">
      <div className={styles.art}>
        <Image src="/games/dashboard/pasapalabra-minimal.png" alt="Rosco de letras azul con detalles en naranja y verde azulado" fill sizes="(max-width: 639px) calc(100vw - 40px), (max-width: 1088px) 45vw, 480px" priority className={styles.image}/>
      </div>
      <div className={styles.body}>
        <h2 id="dashboard-pasapalabra-title">Pasapalabra</h2>
        <p className={styles.description}>Resuelve pistas y completa el rosco antes de que se agote el tiempo.</p>
        <div className={styles.example}>
          <span className={styles.letter} aria-hidden="true">A</span>
          <p><span className={styles.exampleLabel}>Pista de ejemplo · Con la A</span><span className={styles.clue}>Vaso que sale del corazón.</span></p>
        </div>
        <Link href="/pasapalabra" className={`button-primary ${styles.action}`}>Preparar Pasapalabra <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"/></svg></Link>
      </div>
    </article>
    <article className={styles.card} aria-label="Trivial, próximamente">
      <div className={styles.art}>
        <Image src="/games/dashboard/trivial-minimal.png" alt="Tablero con recorrido en espiral, dos fichas y un dado" fill sizes="(max-width: 639px) calc(100vw - 40px), (max-width: 1088px) 45vw, 480px" priority className={styles.image}/>
      </div>
      <div className={styles.body}>
        <h2>Trivial</h2>
        <p className={styles.description}>Tira el dado, responde preguntas y avanza hacia la meta.</p>
        <p className={styles.previewNote}>Estamos integrando el tablero en BioGaMed. Todavía no se pueden iniciar partidas.</p>
        <p className={styles.availability}><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/></svg> Próximamente</p>
      </div>
    </article>
  </div>;
}
