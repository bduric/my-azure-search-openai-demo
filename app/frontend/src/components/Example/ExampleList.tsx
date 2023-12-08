import { Example } from "./Example";

import styles from "./Example.module.css";

export type ExampleModel = {
    text: string;
    value: string;
};

const EXAMPLES: ExampleModel[] = [
    {
        text: "Do I need permit to build a small shed?",
        value: "Do I need permit to build a small shed?"
    },
    {
        text: "Do I need permit to build a porch 200 sqft large and less than one foot above ground?",
        value: "Do I need permit to build a porch 200 sqft large and less than one foot above ground?"
    },
    { text: "What types of work require permits?", value: "What types of work require permits?" }
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
