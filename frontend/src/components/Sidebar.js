import { useState } from 'react';
import { Collapse, List, ListItemButton, ListItemIcon, ListItemText } from '@mui/material';
import { ExpandLess, ExpandMore, FolderOutlined, DescriptionOutlined } from '@mui/icons-material';
import { NavLink } from 'react-router-dom';
function MenuItem({ item, onNavigate }) {
  const [expanded, setExpanded] = useState(false);
  if (item.children?.length) return <>
    <ListItemButton onClick={() => setExpanded(!expanded)} aria-expanded={expanded}>
      <ListItemIcon sx={{ color: 'inherit' }}><FolderOutlined /></ListItemIcon>
      <ListItemText primary={item.label} />{expanded ? <ExpandLess /> : <ExpandMore />}
    </ListItemButton>
    <Collapse in={expanded}><List disablePadding sx={{ pl: 2 }}>
      {item.children.map(child => <MenuItem key={child.menu_id} item={child} onNavigate={onNavigate} />)}
    </List></Collapse>
  </>;
  if (!item.path) return null;
  return <ListItemButton component={NavLink} to={item.path} onClick={onNavigate}
    sx={{ '&.active': { bgcolor: 'rgba(255,255,255,0.18)' } }}>
    <ListItemIcon sx={{ color: 'inherit' }}><DescriptionOutlined /></ListItemIcon>
    <ListItemText primary={item.label} />
  </ListItemButton>;
}
export default function Sidebar({ menu, onNavigate }) {
  return <List component="nav" aria-label="Main navigation">
    {menu.map(item => <MenuItem key={item.menu_id} item={item} onNavigate={onNavigate} />)}
  </List>;
}
