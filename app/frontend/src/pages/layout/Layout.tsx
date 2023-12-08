import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/logo.svg";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";

const Layout = () => {
    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        <h3 className={styles.headerTitle}>GPT + CoVB data | Demo</h3>
                    </Link>
                    <nav>
                        <ul className={styles.headerNavList}>
                            {/* <li>
                                <NavLink to="/" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    Chat
                                </NavLink>
                            </li> */}
                            {/* <li className={styles.headerNavLeftMargin}>
                                <NavLink to="/qa" className={({ isActive }) => (isActive ? styles.headerNavPageLinkActive : styles.headerNavPageLink)}>
                                    Ask a question
                                </NavLink>
                            </li> */}
                            <li className={styles.headerNavLeftMargin}>
                                <a href="https://virginiabeach.gov" target={"_blank"} title="Virginia Beach website link">
                                    <img
                                        src={github}
                                        alt="CoVB logo"
                                        aria-label="Link to CoVB website"
                                        width="20px"
                                        //height="20px"
                                        className={styles.githubLogo}
                                    />
                                </a>
                            </li>
                        </ul>
                    </nav>
                    <h4 className={styles.headerRightText}>AI Powered Search</h4>
                    {useLogin && <LoginButton />}
                </div>
            </header>

            <Outlet />
        </div>
    );
};

export default Layout;
