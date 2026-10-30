import {render,screen} from '@testing-library/react';
import {test,expect} from 'vitest';
test('React renders',()=>{render(<h1>CampusOS-XDU</h1>);expect(screen.getByRole('heading')).toHaveTextContent('CampusOS-XDU');});
