// Node unit tests for the pure helpers in the Teloce debug client.
// Run: node --test tests/js/
import assert from 'node:assert/strict';
import test from 'node:test';

import { hintFor, safeEditorUrl } from '../../src/flaxon/debugging/teloce-client.js';

test('hintFor returns an empty string for messages it does not recognise', () => {
  for (const message of ['', undefined, null, 'TypeError: boom', 'Something went wrong']) {
    assert.equal(hintFor(message), '');
  }
});

test('hintFor is pure: the same message always gives the same hint', () => {
  const message = 'ReferenceError: signal is not defined';
  assert.equal(hintFor(message), hintFor(message));
  assert.equal(
    hintFor(message),
    'signal is not defined. Declare it in the component <script> block, import it, or fix the spelling.',
  );
});

test('hintFor names the undefined identifier', () => {
  assert.match(hintFor('Uncaught ReferenceError: count is not defined'), /^count is not defined\./);
  assert.match(hintFor('signal is not defined'), /<script>/);
  assert.match(hintFor('$state is not defined'), /^\$state is not defined\./);
  assert.match(hintFor('_x is not defined'), /^_x is not defined\./);
});

test('hintFor only treats a real identifier as the name', () => {
  assert.equal(hintFor('a-b is not defined'), '');
  assert.equal(hintFor('store.signal is not defined'), '');
  assert.equal(hintFor('1abc is not defined'), '');
});

test('hintFor explains the common runtime shapes', () => {
  assert.match(hintFor('TypeError: total is not a function'), /^total is not a function\./);
  assert.match(hintFor('TypeError: rows is not iterable'), /^rows is not iterable\./);
  assert.match(
    hintFor("Cannot read properties of undefined (reading 'name')"),
    /The value is undefined when \.name is read\./,
  );
  assert.match(
    hintFor("Cannot set properties of null (setting 'title')"),
    /The value is null when \.title is set\./,
  );
  assert.match(
    hintFor("Cannot read property 'name' of undefined"),
    /The value is undefined when \.name is read\./,
  );
  assert.match(hintFor('RangeError: Maximum call stack size exceeded'), /keeps calling itself/);
  assert.match(hintFor('TypeError: Assignment to constant variable.'), /const count = signal\(0\)/);
  assert.match(hintFor('SyntaxError: Unexpected token \'<\''), /JavaScript arrived as HTML/);
});

test('safeEditorUrl keeps http(s) and editor schemes', () => {
  for (const url of [
    'vscode://file/work/app/ui/app.html:4:17',
    'vscode-insiders://file/work/app/ui/app.html:1:1',
    'https://example.test/open?path=/work/app/ui/app.html',
    '/__editor/open?path=ui/app.html',
  ]) {
    assert.equal(safeEditorUrl(url), url);
  }
});

test('safeEditorUrl refuses schemes a browser must not follow', () => {
  for (const url of [
    'javascript:alert(1)',
    'JavaScript:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox("x")',
    'file:///etc/passwd',
  ]) {
    assert.equal(safeEditorUrl(url), '');
  }
});

test('safeEditorUrl rejects empty and unusable values', () => {
  for (const url of ['', '   ', undefined, null, 'http://[bad']) {
    assert.equal(safeEditorUrl(url), '');
  }
});
