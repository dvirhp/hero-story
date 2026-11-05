import {expect,it,afterEach} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {useState} from 'react';
import {CharacterBuilder} from '../src/personalization/CharacterBuilder';
import {fullCharacterSchema} from '../src/personalization/character';
import {catalog,personalizeTemplate,templateDefaults,templateErrors} from '../src/data/catalog';
afterEach(cleanup);
it('renders only template-supported controls and updates deterministic preview',()=>{
 function Host(){const [values,setValues]=useState({});return <CharacterBuilder schema={{version:'1',fields:['skin','glasses']}} values={values} onChange={setValues} locale="en"/>;}
 render(<Host/>);expect(screen.queryByText('Hair color')).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Deep'}));fireEvent.click(screen.getByLabelText('Glasses'));expect(screen.getByRole('img').getAttribute('data-character')).toContain('"skin":"deep"');expect(screen.getByRole('img').getAttribute('data-character')).toContain('"glasses":true');
});
it('keeps appearance in template choices and never infers presentation from names',()=>{const t=catalog[0],values={...templateDefaults(t),name:'Alex',character_skin:'deep',character_glasses:'true'};const book=personalizeTemplate(t,values,'en');expect(book.character?.presentation).toBe('neutral');expect(book.pages[0].character?.skin).toBe('deep');expect(book.template?.values.character_glasses).toBe('true');expect(templateErrors(t,{...values,character_skin:'unreviewed'}).character_skin).toBe('required');expect(fullCharacterSchema.fields).toContain('eye');});
