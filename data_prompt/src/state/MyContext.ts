import { createContext, useContext } from 'react';

export interface MyContextType {
  visData: any;
  setVisData: React.Dispatch<React.SetStateAction<any>>;

  // 当前被点击选中的图表 spec
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

// 自定义 Hook
export function useMyContext() {
  return useContext(MyContext);
}
