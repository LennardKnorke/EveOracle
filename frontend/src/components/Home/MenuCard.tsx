import { Link } from "react-router-dom";

import "./MenuCard.css";

type MenuCardOption = {
  title: string;
  description: string;
  link: string;
};

function MenuCard({ title, description, link }: MenuCardOption) {
  return (
    <Link to={link} className="card-link">
        <div className="target-card">
            <h2>{title}</h2>
            <p>{description}</p>
        </div>
    </Link>
  );
}

export default MenuCard;