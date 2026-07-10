import { Link } from "react-router-dom";

import "./TargetCard.css";

type TargetCardProps = {
  title: string;
  description: string;
  link: string;
};

function TargetCard({ title, description, link }: TargetCardProps) {
  return (
    <Link to={link} className="card-link">
        <div className="target-card">
            <h2>{title}</h2>
            <p>{description}</p>
        </div>
    </Link>
  );
}

export default TargetCard;