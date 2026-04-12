import React, { useState } from 'react';
import MyContext from './MyContext';

export const MyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [visData, setVisData] = useState<any[]>([]);
  // 存放当前点击选中的可视化 spec
  const [selectedSpec, setSelectedSpec] = useState<any>(null);

  return (
    <MyContext.Provider
      value={{
        visData,
        setVisData,
        selectedSpec,
        setSelectedSpec,
      }}
    >
      {children}
    </MyContext.Provider>
  );
};
