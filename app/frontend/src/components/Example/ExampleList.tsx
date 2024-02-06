import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Can I perform minor car repairs at my residence?",
        value: "Can I perform minor car repairs at my residence?"
    },
    {
        text: "Do I need permit to construct a fence?",
        value: "Do I need permit to construct a fence?"
    },
    { text: "Can I operate my business from my residence?", value: "Can I operate my business from my residence?" }
];

interface Props {
    onExampleClicked: (value: string) => void;
}

export const ExampleList = ({ onExampleClicked }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {EXAMPLES.map((x, i) => (
                <li key={i}>
                    <Example text={x.text} value={x.value} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
