import type { Language } from '../api/contracts';
import { experience } from '../i18n/experience';
import type { ExperienceCopy } from '../i18n/experience';
import {characterFromValues,characterOptions} from './character';
import type {CharacterSchema} from './character';
import {CharacterPreview} from './CharacterPreview';
export function CharacterBuilder({schema,values,onChange,locale}:{schema:CharacterSchema;values:Record<string,string>;onChange:(values:Record<string,string>)=>void;locale:Language}) {
 const e=experience[locale],character=characterFromValues(values,schema);
 return <section className="character-builder"><div className="character-intro"><div><p className="eyebrow">STORYFORGE STUDIO</p><h2>{e.character}</h2><p className="hint">{e.characterNote}</p></div><CharacterPreview character={character} label={e.appearanceSummary}/></div><div className="character-controls">{schema.fields.map(key=>key==='glasses'||key==='freckles'?<label key={key} className="character-toggle"><input type="checkbox" checked={character[key]} onChange={event=>onChange({...values,[`character_${key}`]:String(event.target.checked)})}/>{e[key]}</label>:<fieldset key={key}><legend>{e[key as keyof ExperienceCopy]}</legend><div className="character-choices">{characterOptions[key]!.map(option=><button type="button" key={option.value} aria-pressed={character[key]===option.value} onClick={()=>onChange({...values,[`character_${key}`]:option.value})}><span className={`swatch swatch-${option.value}`} aria-hidden="true"/>{e[option.label]}</button>)}</div></fieldset>)}</div></section>;
}
