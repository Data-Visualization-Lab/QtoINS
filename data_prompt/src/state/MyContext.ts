import { createContext, useContext } from 'react';

export interface MyContextType {
  visData: any;
  setVisData: React.Dispatch<React.SetStateAction<any>>;


  selectedSpec: any;
  setSelectedSpec: React.Dispatch<React.SetStateAction<any>>;
}

const MyContext = createContext<MyContextType>({
  visData: null,
  setVisData: () => {},

  selectedSpec: null,
  setSelectedSpec: () => {},
});

export default MyContext;


export function useMyContext() {
  return useContext(MyContext);
}
