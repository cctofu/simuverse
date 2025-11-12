import { Quantum } from 'ldrs/react';
import 'ldrs/react/Helix.css';

type Props = {
  width?: number;
  height?: number;
};

export default function LoadingScreen({
  width = 400,
  height = 300,
}: Props) {
  return (
    <div
      style={{
        width,
        height,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        margin: '0 auto',
      }}
    >
      <Quantum
            size="45"
            speed="1.75"
            color="black" 
          />
    </div>
  );
}
