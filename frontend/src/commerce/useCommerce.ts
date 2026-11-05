import {useState} from 'react';
import type {Book} from '../domain/book';
import {addLine} from './model';
import type {CartLine,DemoOrder,Format} from './model';
export function useCommerce(){
 const [lines,setLines]=useState<CartLine[]>([]);const [orders,setOrders]=useState<DemoOrder[]>([]);
 const add=(book:Book,format:Format,quantity:number)=>{const next=addLine(lines,book,format,quantity);setLines(next);};
 const update=(id:string,quantity:number)=>{if(!Number.isInteger(quantity)||quantity<1||quantity>10)return;setLines(current=>current.map(line=>line.id===id?{...line,quantity}:line));};
 const remove=(id:string)=>setLines(current=>current.filter(line=>line.id!==id));
 const complete=(order:DemoOrder)=>{setOrders(current=>current.some(item=>item.id===order.id)?current:[order,...current]);setLines([]);};
 return {lines,orders,add,update,remove,complete,count:lines.reduce((sum,line)=>sum+line.quantity,0)};
}
