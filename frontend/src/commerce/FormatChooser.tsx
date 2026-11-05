import {useState} from 'react';
import type {Book} from '../domain/book';
import type {Language} from '../api/contracts';
import {experience,money} from '../i18n/experience';
import {demoOffer,eligible} from './model';
import type {Format} from './model';
import {BookCover} from '../components/BookCover';
export function FormatChooser({book,locale,onAdd}:{book:Book;locale:Language;onAdd:(book:Book,format:Format,quantity:number)=>void}){
 const e=experience[locale];const [format,setFormat]=useState<Format>('hardcover'),[quantity,setQuantity]=useState('1'),[error,setError]=useState(false);
 return <main className="container format-page"><div className="section-title"><div><p className="eyebrow">{e.demoCommerce}</p><h1>{e.configure}</h1><p>{e.formatNote}</p></div><a className="inline-link" href={`#/read/${book.id}`}>{e.reviewBook}</a></div><div className="format-grid"><div className="format-cover"><BookCover title={book.title} art={book.cover} color={book.coverColor} language={book.language} character={book.character}/></div><section><h2 dir="auto">{book.title}</h2><fieldset><legend>{e.format}</legend>{demoOffer.formats.map(option=><label className="format-option" key={option.id}><input type="radio" name="format" value={option.id} checked={format===option.id} onChange={()=>setFormat(option.id)}/><span><strong>{e[option.id]}</strong><small>{e.formatNote}</small></span><bdi>{money(option.unitCents,locale)}</bdi></label>)}</fieldset><label htmlFor="format-quantity">{e.quantity}</label><input id="format-quantity" type="number" min="1" max="10" step="1" value={quantity} onChange={event=>{setQuantity(event.target.value);setError(false);}} aria-invalid={error}/>{error&&<p role="alert" className="field-error">{e.checkoutError}</p>}<button className="button primary" disabled={!eligible(book)} onClick={()=>{try{onAdd(book,format,Number(quantity));}catch{setError(true);}}}>{e.add}</button><p className="hint">{e.demoPrices}</p></section></div></main>;
}
