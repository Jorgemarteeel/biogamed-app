import { PasapalabraGame } from "@/components/Pasapalabra";
export default async function Page({ params }: {
    params: Promise<{
        id: string;
    }>;
}) { const { id } = await params; return /^[1-9]\d*$/.test(id) && Number.isSafeInteger(Number(id)) ? <PasapalabraGame key={id} id={Number(id)}/> : <p>Identificador de partida no válido.</p>; }
