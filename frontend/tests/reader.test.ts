import {expect,it} from 'vitest';
import {physicalSpread} from '../src/components/StoryReader';
it('models opening recto, paired leaves, odd endings and mobile pages',()=>{
 expect(physicalSpread(-1,6,true)).toEqual([]);
 expect(physicalSpread(0,6,true)).toEqual([0]);
 expect(physicalSpread(1,6,true)).toEqual([1,2]);
 expect(physicalSpread(5,6,true)).toEqual([5]);
 expect(physicalSpread(1,6,false)).toEqual([1]);
});
