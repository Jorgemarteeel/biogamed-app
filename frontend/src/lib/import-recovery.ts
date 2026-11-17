export type ImportReference={version:1;userId:string;subjectId:number;blockId:number;categoryId:number;operationId:string};
export function referenceKey(userId:string,categoryId:number,subjectId=0,blockId=0){return categoryId?`biogamed-import:${userId}:${categoryId}`:`biogamed-import:${userId}:0${subjectId||blockId?`:${subjectId}:${blockId}`:""}`;}
export function readReference(storage:Storage,userId:string,subjectId:number,blockId:number,categoryId:number):ImportReference|null{
 const raw=storage.getItem(referenceKey(userId,categoryId,subjectId,blockId));if(raw===null)return null;
 if(raw.length>600)throw new Error("invalid");
 const value=JSON.parse(raw);
 if(!value||Object.keys(value).sort().join()!==['version','userId','subjectId','blockId','categoryId','operationId'].sort().join()||value.version!==1||value.userId!==userId||value.subjectId!==subjectId||value.blockId!==blockId||value.categoryId!==categoryId||typeof value.operationId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value.operationId))throw new Error("invalid");
 return value;
}
export function writeReference(storage:Storage,value:ImportReference){storage.setItem(referenceKey(value.userId,value.categoryId,value.subjectId,value.blockId),JSON.stringify(value));}
