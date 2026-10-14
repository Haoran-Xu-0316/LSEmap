import test from 'node:test';
import assert from 'node:assert/strict';
import {outdoorSkyVisible} from '../src/outdoor-environment.js';

test('isolated frontal elevations retain neutral ground while outdoor street views reveal the sky',()=>{
 assert.equal(outdoorSkyVisible('campus',-.08,true,true),false);
 assert.equal(outdoorSkyVisible('campus',.3,false,true),false);
 assert.equal(outdoorSkyVisible('campus',-.08,false,false),true);
 assert.equal(outdoorSkyVisible('detail',-.08,false,false),true);
 assert.equal(outdoorSkyVisible('interior',.3,true,false),false);
});
