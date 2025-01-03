import { useState } from 'react';
import {
    Box,
    Container,
    TextField,
    Button,
    Paper,
    Typography,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    Checkbox,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    IconButton,
    Chip,
    Stack
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import SaveIcon from '@mui/icons-material/Save';

export default function ASNSearch() {
    const [filter, setFilter] = useState('');
    const [results, setResults] = useState([]);
    const [selected, setSelected] = useState([]);
    const [error, setError] = useState('');
    const [dialogOpen, setDialogOpen] = useState(false);
    const [setName, setSetName] = useState('');

    const handleSearch = async () => {
        try {
            const response = await fetch(`/api/asninfo?filter=${encodeURIComponent(filter)}`);
            if (response.ok) {
                const data = await response.json();
                setResults(data);
                setSelected([]);
                setError('');
            } else {
                setError('Failed to fetch ASN information');
                setResults([]);
            }
        } catch (err) {
            setError('An error occurred while fetching data');
            setResults([]);
        }
    };

    const handleToggleSelect = (cityId) => {
        setSelected(prev =>
            prev.includes(cityId)
                ? prev.filter(id => id !== cityId)
                : [...prev, cityId]
        );
    };

    const handleSaveSet = async () => {
        try {
            const response = await fetch('/api/cityset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: setName,
                    cityIds: selected
                }),
            });

            if (response.ok) {
                setDialogOpen(false);
                setSetName('');
                setSelected([]);
            } else {
                setError('Failed to save city set');
            }
        } catch (err) {
            setError('An error occurred while saving');
        }
    };

    return (
        <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                    ASN Search
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
                    <TextField
                        fullWidth
                        label="Search ASNs"
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        placeholder="e.g. Amazon"
                    />
                    <Button
                        variant="contained"
                        startIcon={<SearchIcon />}
                        onClick={handleSearch}
                        sx={{ minWidth: 120 }}
                    >
                        Search
                    </Button>
                </Box>

                {error && (
                    <Typography color="error" sx={{ mb: 2 }}>
                        {error}
                    </Typography>
                )}

                {results.length > 0 && (
                    <>
                        <TableContainer>
                            <Table>
                                <TableHead>
                                    <TableRow>
                                        <TableCell padding="checkbox">
                                            <Checkbox
                                                indeterminate={selected.length > 0 && selected.length < results.length}
                                                checked={results.length > 0 && selected.length === results.length}
                                                onChange={() => {
                                                    if (selected.length === results.length) {
                                                        setSelected([]);
                                                    } else {
                                                        setSelected(results.map(r => r.cityId));
                                                    }
                                                }}
                                            />
                                        </TableCell>
                                        <TableCell>ASN</TableCell>
                                        <TableCell>Country</TableCell>
                                        <TableCell>Region</TableCell>
                                        <TableCell>Type</TableCell>
                                        <TableCell>IP Range</TableCell>
                                        <TableCell>City ID</TableCell>
                                        <TableCell>Location</TableCell>
                                    </TableRow>
                                </TableHead>
                                <TableBody>
                                    {results.map((result) => (
                                        <TableRow key={result.cityId}>
                                            <TableCell padding="checkbox">
                                                <Checkbox
                                                    checked={selected.includes(result.cityId)}
                                                    onChange={() => handleToggleSelect(result.cityId)}
                                                />
                                            </TableCell>
                                            <TableCell>{result.asn}</TableCell>
                                            <TableCell>{result.country}</TableCell>
                                            <TableCell>{result.region}</TableCell>
                                            <TableCell>{result.asnType}</TableCell>
                                            <TableCell>{result.ipRange.join(' - ')}</TableCell>
                                            <TableCell>{result.cityId}</TableCell>
                                            <TableCell>{`${result.latitude}, ${result.longitude}`}</TableCell>
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </TableContainer>

                        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
                            <Button
                                variant="contained"
                                startIcon={<SaveIcon />}
                                onClick={() => setDialogOpen(true)}
                                disabled={selected.length === 0}
                            >
                                Save as Set
                            </Button>
                        </Box>
                    </>
                )}

                <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
                    <DialogTitle>Save City Set</DialogTitle>
                    <DialogContent>
                        <TextField
                            autoFocus
                            margin="dense"
                            label="Set Name"
                            fullWidth
                            value={setName}
                            onChange={(e) => setSetName(e.target.value)}
                        />
                    </DialogContent>
                    <DialogActions>
                        <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
                        <Button onClick={handleSaveSet} disabled={!setName.trim()}>
                            Save
                        </Button>
                    </DialogActions>
                </Dialog>
            </Paper>
        </Container>
    );
}
