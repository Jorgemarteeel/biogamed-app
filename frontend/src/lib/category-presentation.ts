// Explicit decorative correspondences requested and verified against the source folders.
// This registry never assigns categories, filters questions or infers academic relations.
const CATEGORY_ART=new Map<string,string>([
  ["Erlenmeyer","/categories/erlenmeyer.svg"],
  ["Jeringuilla","/categories/jeringuilla.svg"],
  ["Linfocito","/categories/linfocito.svg"],
  ["Macrófago","/categories/macrofago.svg"],
]);
export function categoryIllustration(name:string){return CATEGORY_ART.get(name.normalize("NFC"))??"/topics/generic.svg";}
