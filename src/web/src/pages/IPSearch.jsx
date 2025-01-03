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
    TableRow
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

export default function IPSearch() {
    const [ip, setIp] = useState('');
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    const handleSearch = async () => {
        try {
            const response = await fetch(`/api/ipinfo?ip=${encodeURIComponent(ip)}`);
            if (response.ok) {
                const data = await response.json();
                setResult(data);
                setError('');
            } else {
                setError('Failed to fetch IP information');
                setResult(null);
            }
        } catch (err) {
            setError('An error occurred while fetching data');
            setResult(null);
        }
    };

    return (
        <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
            <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                    IP Search
                </Typography>
                <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
                    <TextField
                        fullWidth
                        label="Enter IP Address"
                        value={ip}
                        onChange={(e) => setIp(e.target.value)}
                        placeholder="e.g. 2.3.4.5"
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

                {result && (
                    <>
                        <TableContainer>
                            <Table>
                                <TableBody>
                                    <TableRow>
                                        <TableCell component="th" scope="row">ASN</TableCell>
                                        <TableCell>{result.asn}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">Country</TableCell>
                                        <TableCell>{result.country}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">Region</TableCell>
                                        <TableCell>{result.region}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">ASN Type</TableCell>
                                        <TableCell>{result.asnType}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">IP Range</TableCell>
                                        <TableCell>{result.ipRange.join(' - ')}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">City ID</TableCell>
                                        <TableCell>{result.cityId}</TableCell>
                                    </TableRow>
                                    <TableRow>
                                        <TableCell component="th" scope="row">Location</TableCell>
                                        <TableCell>{`${result.latitude}, ${result.longitude}`}</TableCell>
                                    </TableRow>
                                </TableBody>
                            </Table>
                        </TableContainer>

                        <Box sx={{ mt: 3, height: 400 }}>
                            <MapContainer
                                center={[result.latitude, result.longitude]}
                                zoom={10}
                                style={{ height: '100%', width: '100%' }}
                            >
                                <TileLayer
                                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                                />
                                <Marker position={[result.latitude, result.longitude]}>
                                    <Popup>
                                        {result.asn}<br />
                                        {result.cityId}
                                    </Popup>
                                </Marker>
                            </MapContainer>
                        </Box>
                    </>
                )}
            </Paper>
        </Container>
    );
}
