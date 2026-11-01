const illustrations: Record<string, string> = {
  Erlenmeyer: "/topics/erlenmeyer.png",
  Jeringuilla: "/topics/jeringuilla.png",
  Linfocito: "/topics/linfocito.png",
  Macrófago: "/topics/macrofago.png",
};

export function topicIllustration(name: string): string {
  return illustrations[name] ?? "/topics/generic.svg";
}
